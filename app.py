import time
import socket
import uuid
import os
from flask import Flask, render_template, jsonify, request

# Load environment variables from .env file if it exists
def load_env_file():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

load_env_file()

app = Flask(__name__)

# Server-side Game State
game_state = {
    "current_case": 0,    # 0: lobby, 1: Case 1, 2: Case 2, 3: Case 3, 4: Wrap-up & Conclusion
    "phase": "lobby",     # lobby, indictment, debate, voting, result
    "indicators": {
        "corp_market_share": 75,   # starts at 75%
        "startup_fund": 5000,      # starts at 5,000 coins
        "social_benefit": 50       # starts at 50 points
    },
    "timer_end": 0,
    "timer_active": False,
    "timer_duration": 0,
    "votes": {
        "A": 0,
        "B": 0
    },
    "decisions": {         # Stores the winner option of each case (A or B)
        1: None,
        2: None,
        3: None
    }
}

# Tracking connected jury members by their UUID and last poll time
jury_members = {}  # { voter_id: last_poll_timestamp }
voted_members = set() # voter_ids who voted in the CURRENT case

def get_local_ip():
    """Helper to detect the machine's local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable, just triggers local IP lookup
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def clean_inactive_jury():
    """Remove jury members who haven't polled in the last 6 seconds."""
    now = time.time()
    to_remove = [vid for vid, last_seen in jury_members.items() if now - last_seen > 6]
    for vid in to_remove:
        jury_members.pop(vid, None)

def apply_decision(case_num, option):
    """Apply the rules when a jury votes and decision is finalized."""
    # Reset to base values if re-applying
    # We apply the outcome adjustments directly to indicators.
    # Note: MC conclusions will be displayed based on these selections.
    game_state["decisions"][case_num] = option
    
    # Recalculate indicators dynamically from initial state to prevent drift
    corp = 75
    startup = 5000
    social = 50
    
    # Apply Case 1
    if game_state["decisions"][1] == "A":
        corp -= 5
        startup += 500
        social += 10
    elif game_state["decisions"][1] == "B":
        corp += 5
        startup -= 300
        social -= 10
        
    # Apply Case 2
    if game_state["decisions"][2] == "A":
        corp -= 10
        social += 5
    elif game_state["decisions"][2] == "B":
        corp += 15
        startup -= 700
        social -= 5
        
    # Apply Case 3
    if game_state["decisions"][3] == "A":
        startup += 1000
        social += 15
    elif game_state["decisions"][3] == "B":
        startup = 0 # Startup bankrupt
        corp += 5
        social -= 15
        
    game_state["indicators"]["corp_market_share"] = max(0, min(100, corp))
    game_state["indicators"]["startup_fund"] = max(0, startup)
    game_state["indicators"]["social_benefit"] = max(0, min(100, social))

@app.route('/')
@app.route('/presenter')
def presenter():
    local_ip = get_local_ip()
    port = 5000
    jury_url = f"http://{local_ip}:{port}/jury"
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    return render_template('presenter.html', jury_url=jury_url, supabase_url=supabase_url, supabase_key=supabase_key)

@app.route('/jury')
def jury():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    return render_template('jury.html', supabase_url=supabase_url, supabase_key=supabase_key)

@app.route('/api/state', methods=['GET'])
def get_state():
    # Track voter activity
    voter_id = request.args.get('voter_id')
    if voter_id:
        jury_members[voter_id] = time.time()
        
    clean_inactive_jury()
    
    # Calculate remaining time
    remaining = 0
    if game_state["timer_active"]:
        remaining = int(game_state["timer_end"] - time.time())
        if remaining <= 0:
            remaining = 0
            game_state["timer_active"] = False
            
    # Calculate percentage votes
    total_votes = game_state["votes"]["A"] + game_state["votes"]["B"]
    votes_pct = {"A": 0, "B": 0}
    if total_votes > 0:
        votes_pct["A"] = round((game_state["votes"]["A"] / total_votes) * 100)
        votes_pct["B"] = round((game_state["votes"]["B"] / total_votes) * 100)
        
    # Check if this voter has voted in the current case
    has_voted = voter_id in voted_members
            
    state_response = {
        "current_case": game_state["current_case"],
        "phase": game_state["phase"],
        "indicators": game_state["indicators"],
        "timer_remaining": remaining,
        "timer_active": game_state["timer_active"],
        "timer_duration": game_state["timer_duration"],
        "votes": game_state["votes"],
        "votes_pct": votes_pct,
        "total_votes": total_votes,
        "decisions": game_state["decisions"],
        "jury_count": len(jury_members),
        "has_voted": has_voted
    }
    return jsonify(state_response)

@app.route('/api/vote', methods=['POST'])
def submit_vote():
    data = request.json or {}
    voter_id = data.get('voter_id')
    option = data.get('option')  # 'A' or 'B'
    
    if game_state["phase"] != "voting":
        return jsonify({"success": False, "error": "Voting is not active."}), 400
        
    if not voter_id:
        return jsonify({"success": False, "error": "Voter ID required."}), 400
        
    if voter_id in voted_members:
        return jsonify({"success": False, "error": "You have already voted in this case."}), 400
        
    if option not in ['A', 'B']:
        return jsonify({"success": False, "error": "Invalid voting option."}), 400
        
    game_state["votes"][option] += 1
    voted_members.add(voter_id)
    
    return jsonify({"success": True})

@app.route('/api/control', methods=['POST'])
def control_game():
    data = request.json or {}
    action = data.get('action')
    
    if action == "reset":
        game_state["current_case"] = 0
        game_state["phase"] = "lobby"
        game_state["indicators"] = {
            "corp_market_share": 75,
            "startup_fund": 5000,
            "social_benefit": 50
        }
        game_state["timer_active"] = False
        game_state["votes"] = {"A": 0, "B": 0}
        game_state["decisions"] = {1: None, 2: None, 3: None}
        voted_members.clear()
        return jsonify({"success": True})
        
    elif action == "set_phase":
        case_num = data.get('case')
        phase = data.get('phase') # lobby, indictment, debate, voting, result
        
        # If moving to a new case or voting phase, clear votes
        if phase in ["indictment", "debate"]:
            game_state["votes"] = {"A": 0, "B": 0}
            voted_members.clear()
            
        game_state["current_case"] = case_num
        game_state["phase"] = phase
        game_state["timer_active"] = False
        
        return jsonify({"success": True})
        
    elif action == "trigger_timer":
        duration = data.get('duration', 60)
        game_state["timer_active"] = True
        game_state["timer_duration"] = duration
        game_state["timer_end"] = time.time() + duration
        return jsonify({"success": True})
        
    elif action == "stop_timer":
        game_state["timer_active"] = False
        return jsonify({"success": True})
        
    elif action == "apply_judgment":
        case_num = game_state["current_case"]
        # If manual option is specified, use that. Otherwise use majority vote.
        option = data.get('option')
        if not option:
            if game_state["votes"]["A"] >= game_state["votes"]["B"]:
                option = "A"
            else:
                option = "B"
        
        apply_decision(case_num, option)
        game_state["phase"] = "result"
        game_state["timer_active"] = False
        return jsonify({"success": True, "selected_option": option})
        
    return jsonify({"success": False, "error": "Invalid action."}), 400

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("=" * 60)
    print(f"Courtroom Game Server is running!")
    print(f"Presenter link: http://localhost:5000")
    print(f"Jury mobile voting link: http://{local_ip}:5000/jury")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
