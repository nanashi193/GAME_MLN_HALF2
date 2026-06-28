# GAME_MLN_HALF2

Flask app for a courtroom voting game. Supports two realtime modes:

- **Supabase Realtime broadcast** when `.env` contains Supabase config.
- **Local Flask polling fallback** when Supabase config is missing.

---

## 🚀 Deploy lên Render.com (Miễn phí, không cần cùng WiFi)

### Bước 1 — Tạo Supabase Project (Real-time voting)

1. Vào [supabase.com](https://supabase.com) → **Start your project** → đăng ký miễn phí
2. Tạo project mới (chọn region **Southeast Asia**)
3. Sau khi tạo xong, vào **Project Settings → API**
4. Copy:
   - **Project URL** → dùng làm `SUPABASE_URL`
   - **anon / public** key → dùng làm `SUPABASE_ANON_KEY`

### Bước 2 — Push code lên GitHub

```powershell
git add .
git commit -m "Add deploy config for Render"
git push
```

### Bước 3 — Deploy lên Render

1. Vào [render.com](https://render.com) → đăng ký / đăng nhập bằng GitHub
2. Click **New → Web Service**
3. Chọn repo **GAME_MLN_HALF2** → **Connect**
4. Render sẽ tự detect `render.yaml` — kiểm tra lại:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Cuộn xuống phần **Environment Variables**, thêm:
   | Key | Value |
   |-----|-------|
   | `SUPABASE_URL` | URL từ bước 1 |
   | `SUPABASE_ANON_KEY` | Key từ bước 1 |
6. Click **Deploy Web Service**
7. Đợi ~2-3 phút → Render cấp link dạng `https://game-mln-half2.onrender.com`

### Bước 4 — Cấu hình PUBLIC_BASE_URL

Sau khi deploy xong và biết URL chính xác:

1. Vào Render dashboard → **Environment**
2. Thêm biến: `PUBLIC_BASE_URL` = `https://game-mln-half2.onrender.com` (URL thực của bạn)
3. Click **Save Changes** → Render tự restart

### Kết quả

| Người dùng | Link |
|---|---|
| Presenter (MC) | `https://your-app.onrender.com` |
| Jury (điện thoại) | `https://your-app.onrender.com/jury` |

---

## 💻 Chạy Local (cùng WiFi)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `.env` và điền Supabase config:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
```

Chạy:

```powershell
python app.py
```

- Presenter: `http://localhost:5000`
- Jury (điện thoại cùng WiFi): URL được in ra terminal, ví dụ `http://192.168.1.10:5000/jury`

---

## ⚙️ Supabase Socket Notes

App dùng Supabase Realtime broadcast channel `courtroom`; không cần database table.

Giữ màn hình presenter mở trong suốt game. Presenter nhận votes từ jury qua socket rồi broadcast state mới đến tất cả clients.
