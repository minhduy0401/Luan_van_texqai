# Hướng Dẫn Cài Đặt TEXTQAI | Installation Guide

> **Phiên bản / Version:** 1.0 &nbsp;|&nbsp; **Cập nhật / Updated:** 06/2026

---

## 🇻🇳 TIẾNG VIỆT

### Mục lục
1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Clone mã nguồn từ GitHub](#2-clone-mã-nguồn-từ-github)
3. [Cài đặt môi trường Python](#3-cài-đặt-môi-trường-python)
4. [Cài đặt cơ sở dữ liệu MySQL](#4-cài-đặt-cơ-sở-dữ-liệu-mysql)
5. [Cấu hình biến môi trường](#5-cấu-hình-biến-môi-trường)
6. [Khởi động ứng dụng](#6-khởi-động-ứng-dụng)
7. [Tạo tài khoản admin](#7-tạo-tài-khoản-admin)
8. [Deploy production (tùy chọn)](#8-deploy-production-tùy-chọn)
9. [Xử lý lỗi thường gặp](#9-xử-lý-lỗi-thường-gặp)

---

### 1. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|-----------|-------------------|
| Python | 3.10+ |
| Git | 2.30+ |
| MySQL | 8.0+ |
| RAM | 2 GB trở lên |
| Hệ điều hành | Windows 10 / Ubuntu 20.04+ / macOS 12+ |

**Tài khoản API cần có:**
- [OpenRouter](https://openrouter.ai) hoặc [Google AI Studio](https://aistudio.google.com) (Gemini) — để chạy AI
- [ngrok](https://ngrok.com) (tùy chọn) — để expose local server ra internet

---

### 2. Clone mã nguồn từ GitHub

#### Bước 1 – Cài Git (nếu chưa có)
- Windows: tải tại [git-scm.com](https://git-scm.com/download/win)
- Ubuntu: `sudo apt install git`
- macOS: `brew install git` hoặc cài Xcode Command Line Tools

#### Bước 2 – Clone repository
Mở terminal/cmd, chọn thư mục muốn đặt dự án, rồi chạy:

```bash
git clone https://github.com/minhduy0401/Luan_van_texqai.git
cd Luan_van_texqai
```

#### Bước 3 – (Tùy chọn) Cập nhật code sau này
Khi repository có phiên bản mới:

```bash
git pull
```

> 💡 Nếu dùng SSH: `git clone git@github.com:minhduy0401/Luan_van_texqai.git`

---

### 3. Cài đặt môi trường Python

#### Bước 1 – Tạo môi trường ảo
```bash
python -m venv venv
```

#### Bước 2 – Kích hoạt môi trường ảo
```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

#### Bước 3 – Cài dependencies
```bash
pip install -r requirements.txt
```

> ⏱️ Quá trình cài đặt mất khoảng 2–5 phút tùy tốc độ mạng.

---

### 4. Cài đặt cơ sở dữ liệu MySQL

#### Bước 1 – Tạo database
Đăng nhập MySQL và chạy:
```sql
CREATE DATABASE textqai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'textqai_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON textqai.* TO 'textqai_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Bước 2 – Ghi nhớ thông tin kết nối
```
Host:     localhost
Port:     3306
Database: textqai
User:     textqai_user
Password: your_password
```

> 💡 Bảng sẽ được tự động tạo khi chạy `python init_db.py` hoặc khởi động app lần đầu (`db.create_all()`).

#### Bước 3 – Tạo bảng (schema)
```bash
python init_db.py
```

Hoặc tạo database bằng file SQL:
```bash
mysql -u root -p < database/init.sql
```

---

### 5. Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc dự án:

```env
# ── Cơ sở dữ liệu ────────────────────────────────
DATABASE_URI=mysql+mysqlconnector://textqai_user:your_password@localhost/textqai

# ── Bảo mật Flask ────────────────────────────────
SECRET_KEY=your-very-secret-key-change-this

# ── AI Provider (chọn một) ───────────────────────
# Option A: OpenRouter (hỗ trợ nhiều model)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
OPENROUTER_MODEL=google/gemini-2.5-flash-lite

# Option B: Gemini trực tiếp
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXX
GEMINI_MODEL=gemini-2.5-flash-lite

# ── Google OAuth (cho đăng nhập Google) ──────────
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxx

# ── Email SMTP (cho quên mật khẩu) ───────────────
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your-app-password
```

> 🔐 **Quan trọng:** Không commit file `.env` lên Git. File `.gitignore` đã có sẵn rule này.

---

### 6. Khởi động ứng dụng

#### Development (phát triển local)
```bash
python app.py
```
Truy cập: `http://localhost:5000`

---

### 7. Tạo tài khoản admin

Hệ thống **không** có admin mặc định. Người cài đặt cần tạo admin sau bước trên.

#### Cách 1 — Script (khuyến nghị)

```bash
python create_admin.py
```

Nhập username, email (có thể bỏ qua), mật khẩu → tài khoản admin được tạo với quyền truy cập `/admin`.

Hoặc truyền tham số:

```bash
python create_admin.py --username admin --email admin@example.com
```

#### Cách 2 — Đăng ký web rồi nâng quyền

1. Mở `http://localhost:5000/register` → đăng ký tài khoản thường
2. Chạy:

```bash
python create_admin.py --username ten_tai_khoan --promote
```

#### Cách 3 — SQL trực tiếp (MySQL)

Sau khi đã có user (đăng ký qua web hoặc script):

```sql
UPDATE users SET is_admin = 1 WHERE username = 'ten_tai_khoan';
```

Đăng nhập lại tại `/login` — menu **Admin** sẽ hiện trên thanh điều hướng.

---

### 8. Deploy production (tùy chọn)

#### Dùng Waitress (Windows server)
```bash
pip install waitress
# app.py tự động dùng Waitress nếu đã cài
python app.py
```

#### Dùng Gunicorn (Linux/macOS)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Dùng Nginx làm reverse proxy
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 9. Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| `ModuleNotFoundError` | Chưa kích hoạt venv | Chạy `venv\Scripts\activate` |
| `Access denied for user` | Sai thông tin MySQL | Kiểm tra lại `DATABASE_URI` trong `.env` |
| `API key invalid` | Key AI chưa đúng | Kiểm tra OpenRouter/Gemini key |
| Port 5000 đang dùng | Có app khác chiếm cổng | Dừng app cũ hoặc đổi port |
| PDF không đọc được | File PDF là ảnh scan | Dùng OCR trước khi upload |

---
---

## 🇬🇧 ENGLISH

### Table of Contents
1. [System Requirements](#1-system-requirements)
2. [Clone Source from GitHub](#2-clone-source-from-github)
3. [Set Up Python Environment](#3-set-up-python-environment)
4. [Set Up MySQL Database](#4-set-up-mysql-database)
5. [Configure Environment Variables](#5-configure-environment-variables)
6. [Start the Application](#6-start-the-application)
7. [Create Admin Account](#7-create-admin-account)
8. [Production Deployment (Optional)](#8-production-deployment-optional)
9. [Troubleshooting](#9-troubleshooting)

---

### 1. System Requirements

| Component | Minimum Version |
|-----------|----------------|
| Python | 3.10+ |
| Git | 2.30+ |
| MySQL | 8.0+ |
| RAM | 2 GB or more |
| OS | Windows 10 / Ubuntu 20.04+ / macOS 12+ |

**Required API Accounts:**
- [OpenRouter](https://openrouter.ai) or [Google AI Studio](https://aistudio.google.com) (Gemini) — for AI features
- [ngrok](https://ngrok.com) (optional) — to expose local server to the internet

---

### 2. Clone Source from GitHub

#### Step 1 – Install Git (if not already installed)
- Windows: download from [git-scm.com](https://git-scm.com/download/win)
- Ubuntu: `sudo apt install git`
- macOS: `brew install git` or install Xcode Command Line Tools

#### Step 2 – Clone the repository
Open a terminal, navigate to your desired folder, then run:

```bash
git clone https://github.com/minhduy0401/Luan_van_texqai.git
cd Luan_van_texqai
```

#### Step 3 – (Optional) Pull updates later
When new code is pushed to the repository:

```bash
git pull
```

> 💡 For SSH: `git clone git@github.com:minhduy0401/Luan_van_texqai.git`

---

### 3. Set Up Python Environment

#### Step 1 – Create virtual environment
```bash
python -m venv venv
```

#### Step 2 – Activate virtual environment
```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

#### Step 3 – Install dependencies
```bash
pip install -r requirements.txt
```

> ⏱️ Installation takes approximately 2–5 minutes depending on network speed.

---

### 4. Set Up MySQL Database

#### Step 1 – Create the database
Log into MySQL and run:
```sql
CREATE DATABASE textqai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'textqai_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON textqai.* TO 'textqai_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Step 2 – Note your connection details
```
Host:     localhost
Port:     3306
Database: textqai
User:     textqai_user
Password: your_password
```

> 💡 Tables are created by running `python init_db.py` or on first app startup (`db.create_all()`).

#### Step 3 – Create tables (schema)
```bash
python init_db.py
```

Or create the database from SQL file:
```bash
mysql -u root -p < database/init.sql
```

---

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# ── Database ──────────────────────────────────────
DATABASE_URI=mysql+mysqlconnector://textqai_user:your_password@localhost/textqai

# ── Flask Security ────────────────────────────────
SECRET_KEY=your-very-secret-key-change-this

# ── AI Provider (choose one) ─────────────────────
# Option A: OpenRouter (multi-model support)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
OPENROUTER_MODEL=google/gemini-2.5-flash-lite

# Option B: Direct Gemini API
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXX
GEMINI_MODEL=gemini-2.5-flash-lite

# ── Google OAuth (for Google login) ──────────────
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxx

# ── SMTP Email (for password recovery) ───────────
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your-app-password
```

> 🔐 **Important:** Never commit the `.env` file to Git. The `.gitignore` already excludes it.

---

### 6. Start the Application

#### Development (local)
```bash
python app.py
```
Access at: `http://localhost:5000`

---

### 7. Create Admin Account

There is **no default admin account**. The installer must create one after the app runs.

#### Option 1 — Script (recommended)

```bash
python create_admin.py
```

Enter username, email (optional), and password → admin account with access to `/admin`.

```bash
python create_admin.py --username admin --email admin@example.com
```

#### Option 2 — Register on web, then promote

1. Open `http://localhost:5000/register` and create a normal account
2. Run:

```bash
python create_admin.py --username your_username --promote
```

#### Option 3 — Direct SQL (MySQL)

```sql
UPDATE users SET is_admin = 1 WHERE username = 'your_username';
```

Log in again at `/login` — the **Admin** menu appears in the navigation bar.

#### Expose to internet with ngrok (for mobile testing)
```bash
# Terminal 1
python app.py

# Terminal 2
ngrok http --domain=your-domain.ngrok-free.dev 5000
```

---

### 8. Production Deployment (Optional)

#### Using Waitress (Windows server)
```bash
pip install waitress
# app.py automatically uses Waitress if installed
python app.py
```

#### Using Gunicorn (Linux/macOS)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Using Nginx as a Reverse Proxy
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 9. Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Virtual env not activated | Run `venv\Scripts\activate` |
| `Access denied for user` | Wrong MySQL credentials | Check `DATABASE_URI` in `.env` |
| `API key invalid` | Incorrect AI key | Verify OpenRouter/Gemini key |
| Port 5000 in use | Another app occupying port | Stop other app or change port |
| PDF not readable | PDF is a scanned image | Run OCR on PDF before uploading |
