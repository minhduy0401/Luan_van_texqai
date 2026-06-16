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
10. [Giao diện đa ngôn ngữ Anh/Việt](#10-giao-diện-đa-ngôn-ngữ-anhviệt)

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

### 10. Giao diện đa ngôn ngữ (Anh/Việt)

TEXTQAI hỗ trợ chuyển **Tiếng Việt ↔ English** trên giao diện web (navbar, nút, thông báo…). Đây là cơ chế **tự viết trong dự án**, **không** dùng Flask-Babel, gettext hay thư viện i18n bên thứ ba.

#### Công nghệ sử dụng

| Thành phần | Công nghệ / File | Vai trò |
|-----------|------------------|---------|
| Lưu ngôn ngữ đang chọn | **Flask Session** (`session['lang']`) | Giá trị `'en'` hoặc `'vi'`, mặc định `'en'` |
| Lưu trên trình duyệt | **Cookie** + **localStorage** (`app_lang`) | Giữ ngôn ngữ trên iOS WebView / app mobile |
| Từ điển dịch | **`utils/translations.py`** | Dict Python `TRANSLATIONS` — key tiếng Việt → `{en, vi}` |
| Inject vào template | **`app.py`** — `@app.context_processor` | Cung cấp `t()` và `current_lang` cho mọi trang Jinja2 |
| Chuyển ngôn ngữ | Route **`GET /set-language/<lang>`** | Ghi session rồi redirect về trang trước |
| Hiển thị HTML | **Jinja2** trong `templates/` | `{{ t('...') }}` hoặc `{% if current_lang == 'en' %}` |
| Thông báo backend | Helper **`_bi(en, vi)`** trong `app.py` | Flash message / logic server song ngữ |

#### Luồng hoạt động

```
Người dùng bấm EN/VI (base.html)
    → GET /set-language/en hoặc /set-language/vi
    → session['lang'] = 'en' | 'vi'
    → Template gọi t('Trang chủ') → tra TRANSLATIONS → hiển thị "Home" hoặc "Trang chủ"
```

#### File cần biết khi chỉnh sửa / mở rộng

| File | Nội dung |
|------|----------|
| `utils/translations.py` | Thêm/chỉnh chuỗi UI: `"Tiếng Việt gốc": {"en": "English", "vi": "Tiếng Việt gốc"}` |
| `app.py` | `inject_translations()`, `set_language()`, `_bi()` |
| `templates/base.html` | Nút chuyển ngôn ngữ + JS lưu cookie/localStorage |

**Ví dụ thêm chuỗi mới** — trong template:

```html
{{ t('Sinh câu hỏi') }}
```

Thêm vào `utils/translations.py`:

```python
"Sinh câu hỏi": {
    "en": "Generate Questions",
    "vi": "Sinh câu hỏi",
},
```

#### Lưu ý quan trọng

- **Giao diện web** (nút EN/VI) và **ngôn ngữ câu hỏi/đáp án AI** là **hai hệ thống riêng**.
- Câu hỏi/đáp án do AI sinh ra theo **ngôn ngữ PDF** (hàm `_is_english_content()` trong `services/pipeline.py`), không theo nút chuyển ngôn ngữ trên navbar.
- Không cần cài thêm package cho i18n; chỉ cần Flask + Jinja2 có sẵn trong `requirements.txt`.

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
10. [Bilingual UI (English/Vietnamese)](#10-bilingual-ui-englishvietnamese)

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

---

### 10. Bilingual UI (English/Vietnamese)

TEXTQAI supports **Vietnamese ↔ English** switching for the web UI (navbar, buttons, flash messages, etc.). This is a **custom in-project mechanism** — it does **not** use Flask-Babel, gettext, or any third-party i18n library.

#### Technology stack

| Component | Technology / File | Role |
|-----------|-------------------|------|
| Store selected language | **Flask Session** (`session['lang']`) | Values `'en'` or `'vi'`, default `'en'` |
| Browser persistence | **Cookie** + **localStorage** (`app_lang`) | Keeps language on iOS WebView / mobile app |
| Translation dictionary | **`utils/translations.py`** | Python dict `TRANSLATIONS` — Vietnamese key → `{en, vi}` |
| Template injection | **`app.py`** — `@app.context_processor` | Provides `t()` and `current_lang` to all Jinja2 pages |
| Language switch | Route **`GET /set-language/<lang>`** | Writes session then redirects back |
| HTML rendering | **Jinja2** in `templates/` | `{{ t('...') }}` or `{% if current_lang == 'en' %}` |
| Backend messages | **`_bi(en, vi)`** helper in `app.py` | Bilingual flash messages / server logic |

#### Flow

```
User clicks EN/VI (base.html)
    → GET /set-language/en or /set-language/vi
    → session['lang'] = 'en' | 'vi'
    → Template calls t('Trang chủ') → lookup TRANSLATIONS → shows "Home" or "Trang chủ"
```

#### Files to edit when extending translations

| File | Purpose |
|------|---------|
| `utils/translations.py` | Add/edit UI strings: `"Vietnamese text": {"en": "English", "vi": "Vietnamese text"}` |
| `app.py` | `inject_translations()`, `set_language()`, `_bi()` |
| `templates/base.html` | Language toggle button + JS for cookie/localStorage |

**Example — add a new string** in template:

```html
{{ t('Sinh câu hỏi') }}
```

Add to `utils/translations.py`:

```python
"Sinh câu hỏi": {
    "en": "Generate Questions",
    "vi": "Sinh câu hỏi",
},
```

#### Important notes

- **Web UI language** (EN/VI toggle) and **AI question/answer language** are **separate systems**.
- Generated Q&A follows the **PDF document language** (`_is_english_content()` in `services/pipeline.py`), not the navbar language switch.
- No extra i18n packages required — Flask + Jinja2 from `requirements.txt` is sufficient.
