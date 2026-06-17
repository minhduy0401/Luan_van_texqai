# Hướng Dẫn Cài Đặt TEXTQAI | Installation Guide

> **Phiên bản / Version:** 1.1 &nbsp;|&nbsp; **Cập nhật / Updated:** 06/2026  
> **CSDL / Database:** PostgreSQL 14+ (không dùng MySQL / XAMPP)

---

## 🇻🇳 TIẾNG VIỆT

### Mục lục
1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Clone mã nguồn từ GitHub](#2-clone-mã-nguồn-từ-github)
3. [Cài đặt môi trường Python](#3-cài-đặt-môi-trường-python)
4. [Cài đặt PostgreSQL](#4-cài-đặt-postgresql)
5. [Cấu hình bootstrap](#5-cấu-hình-bootstrap-instancebootstrapjson)
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
| PostgreSQL | 14+ (cài riêng — **không cần XAMPP/MySQL**) |
| Driver Python | `psycopg2-binary` (có trong `requirements.txt`) |
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

### 4. Cài đặt PostgreSQL

TEXTQAI dùng **PostgreSQL** qua SQLAlchemy URI dạng `postgresql+psycopg2://...`. Không cần cài XAMPP hay MySQL.

#### Bước 1 – Cài PostgreSQL

- **Windows:** [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) hoặc:
  ```powershell
  winget install PostgreSQL.PostgreSQL.17
  ```
- **Ubuntu:** `sudo apt install postgresql postgresql-contrib`
- **macOS:** `brew install postgresql@16 && brew services start postgresql@16`

Ghi nhớ mật khẩu user **`postgres`** khi cài.

**Docker** (tùy chọn):

```bash
docker run -d --name textqai-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

#### Bước 2 – Tạo database và user

Từ thư mục gốc dự án:

```bash
psql -U postgres -f database/init_postgres.sql
psql -U postgres -d luanvan_ai -c "GRANT ALL ON SCHEMA public TO textqai_user;"
psql -U postgres -d luanvan_ai -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO textqai_user;"
```

> **Windows:** nếu lệnh `psql` không tìm thấy, dùng đường dẫn đầy đủ, ví dụ:
> `"D:\PostgresSQL\bin\psql.exe" -U postgres -f database\init_postgres.sql`

> **Dev nhanh:** có thể bỏ qua `textqai_user` và dùng luôn user `postgres` trong `bootstrap.json`.

#### Bước 3 – Thông tin kết nối

```
Host:     127.0.0.1
Port:     5432
Database: luanvan_ai
User:     postgres (dev) hoặc textqai_user
Password: (mật khẩu đã đặt khi cài)
```

#### Bước 4 – Tạo bảng (schema)

```bash
python init_db.py
```

Script gọi `db.create_all()` và seed cài đặt mặc định vào `system_settings`. Các bảng chính:

| Bảng | Mô tả |
|------|--------|
| `users`, `user_auth_providers` | Tài khoản, đăng nhập local / Google |
| `documents`, `qa_results` | PDF và câu hỏi đã sinh |
| `agent1/2/3_evaluation_logs` | Log pipeline AI |
| `credit_packages`, `subscription_packages`, `transactions` | Thanh toán |
| `feedbacks`, `system_settings` | Phản hồi, cấu hình admin |

> Lần chạy `python app.py` cũng tự gọi `db.create_all()` nếu chưa có bảng.

#### Chuyển từ MySQL / XAMPP (legacy)

Dữ liệu MySQL **không tự chuyển** sang PostgreSQL. Cài PostgreSQL mới → chạy `init_db.py` → import cấu hình từ `.env` cũ (nếu có):

```bash
python migrate_env_to_db.py
```

Script SQL MySQL cũ (tham khảo): `database/init_mysql.sql`.

---

### 5. Cấu hình bootstrap (`instance/bootstrap.json`)

App chỉ cần **một file bootstrap** để biết cách kết nối DB lần đầu. **Không dùng `.env`** cho database URI.

#### Bước 1 – Tạo file bootstrap

```bash
python setup_bootstrap.py
```

#### Bước 2 – Sửa `instance/bootstrap.json`

```json
{
  "database_uri": "postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/luanvan_ai",
  "secret_key": "your-secret-key-change-this"
}
```

| Trường | Ý nghĩa |
|--------|---------|
| `database_uri` | Chuỗi kết nối PostgreSQL — dùng **`postgresql+psycopg2`**, không phải `mysql+mysqlconnector` |
| `secret_key` | Khóa session Flask (có thể ghi đè sau trong Admin) |

> Mật khẩu có ký tự đặc biệt (`@`, `#`, `%`…) phải [URL-encode](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls) trong URI.

#### Bước 3 – Cấu hình còn lại qua Admin

Sau khi app chạy được, vào **Admin → Cài đặt hệ thống** (`system_settings`):

- API key: OpenRouter / OpenAI / Gemini  
- Google OAuth (Client ID, Secret, Redirect URI)  
- VNPAY, SePay, thông tin ngân hàng  
- Bật/tắt OCR, model AI, credits mặc định  

**Import từ `.env` cũ (một lần):**

```bash
python migrate_env_to_db.py
```

> 🔐 Không commit `instance/bootstrap.json` lên Git (đã có trong `.gitignore`).

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

#### Cách 3 — SQL trực tiếp (PostgreSQL)

Sau khi đã có user (đăng ký qua web hoặc script):

```sql
UPDATE users SET is_admin = TRUE WHERE username = 'ten_tai_khoan';
```

Đăng nhập lại tại `/login` — menu **Admin** sẽ hiện trên thanh điều hướng.

#### Expose ra internet với ngrok (test mobile / OAuth)

```bash
# Terminal 1
python app.py

# Terminal 2
ngrok http --domain=your-domain.ngrok-free.dev 5000
```

Cập nhật **Google Redirect URI** trong Admin cho khớp URL ngrok.

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
| `ModuleNotFoundError: psycopg2` | Chưa cài driver PostgreSQL | `pip install -r requirements.txt` hoặc `python -m pip install psycopg2-binary` |
| `ModuleNotFoundError` (khác) | Chưa kích hoạt venv | `venv\Scripts\activate` (Windows) |
| `could not connect to server` | PostgreSQL chưa chạy | Khởi động service PostgreSQL (Services → `postgresql-x64-*`) |
| `password authentication failed` | Sai mật khẩu / user | Sửa `database_uri` trong `instance/bootstrap.json` |
| `database "luanvan_ai" does not exist` | Chưa tạo DB | Chạy `database/init_postgres.sql` |
| `relation "users" does not exist` | Chưa tạo bảng | Chạy `python init_db.py` |
| `No such client: google` | OAuth chưa có trong DB | Chạy `migrate_env_to_db.py` hoặc cấu hình Admin → Tích hợp |
| `API key invalid` | Key AI chưa đúng | Admin → Cài đặt → nhập OpenRouter/Gemini key |
| Port 5000 đang dùng | Có app khác chiếm cổng | Dừng app cũ hoặc đổi port |
| PDF không đọc được | File PDF là ảnh scan | Bật OCR trong Admin hoặc OCR trước khi upload |

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
4. [Set Up PostgreSQL Database](#4-set-up-postgresql-database)
5. [Bootstrap config](#5-bootstrap-config-instancebootstrapjson)
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
| PostgreSQL | 14+ (standalone — **no XAMPP/MySQL required**) |
| Python driver | `psycopg2-binary` (included in `requirements.txt`) |
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

### 4. Set Up PostgreSQL Database

TEXTQAI uses **PostgreSQL** via SQLAlchemy URI `postgresql+psycopg2://...`. XAMPP/MySQL is **not** required.

#### Step 1 – Install PostgreSQL

- **Windows:** [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) or:
  ```powershell
  winget install PostgreSQL.PostgreSQL.17
  ```
- **Ubuntu:** `sudo apt install postgresql postgresql-contrib`
- **macOS:** `brew install postgresql@16 && brew services start postgresql@16`

Remember the **`postgres`** user password during installation.

**Docker** (optional):

```bash
docker run -d --name textqai-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

#### Step 2 – Create database and user

From the project root:

```bash
psql -U postgres -f database/init_postgres.sql
psql -U postgres -d luanvan_ai -c "GRANT ALL ON SCHEMA public TO textqai_user;"
psql -U postgres -d luanvan_ai -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO textqai_user;"
```

> **Windows:** if `psql` is not in PATH, use the full path, e.g.  
> `"D:\PostgresSQL\bin\psql.exe" -U postgres -f database\init_postgres.sql`

> **Quick dev:** you may skip `textqai_user` and use the `postgres` user in `bootstrap.json`.

#### Step 3 – Connection details

```
Host:     127.0.0.1
Port:     5432
Database: luanvan_ai
User:     postgres (dev) or textqai_user
Password: (password set during install)
```

#### Step 4 – Create tables (schema)

```bash
python init_db.py
```

This runs `db.create_all()` and seeds defaults into `system_settings`. Main tables:

| Table | Description |
|-------|-------------|
| `users`, `user_auth_providers` | Accounts, local / Google login |
| `documents`, `qa_results` | PDFs and generated Q&A |
| `agent1/2/3_evaluation_logs` | AI pipeline logs |
| `credit_packages`, `subscription_packages`, `transactions` | Payments |
| `feedbacks`, `system_settings` | Feedback, admin config |

> First run of `python app.py` also calls `db.create_all()` if tables are missing.

#### Migrating from MySQL / XAMPP (legacy)

MySQL data is **not** migrated automatically. Set up fresh PostgreSQL → run `init_db.py` → import old `.env` if needed:

```bash
python migrate_env_to_db.py
```

Legacy MySQL SQL script: `database/init_mysql.sql`.

---

### 5. Bootstrap config (`instance/bootstrap.json`)

The app needs **only one bootstrap file** for the initial DB connection. **Do not use `.env`** for the database URI.

#### Step 1 – Create bootstrap file

```bash
python setup_bootstrap.py
```

#### Step 2 – Edit `instance/bootstrap.json`

```json
{
  "database_uri": "postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/luanvan_ai",
  "secret_key": "your-secret-key-change-this"
}
```

| Field | Meaning |
|-------|---------|
| `database_uri` | PostgreSQL connection string — use **`postgresql+psycopg2`**, not `mysql+mysqlconnector` |
| `secret_key` | Flask session key (can be overridden later in Admin) |

> URL-encode special characters in the password (`@`, `#`, `%`, …) in the URI.

#### Step 3 – Configure everything else in Admin

After the app starts, open **Admin → System Settings** (`system_settings`):

- API keys: OpenRouter / OpenAI / Gemini  
- Google OAuth (Client ID, Secret, Redirect URI)  
- VNPAY, SePay, bank details  
- OCR toggle, AI model, default credits  

**Import from legacy `.env` (once):**

```bash
python migrate_env_to_db.py
```

> 🔐 Do not commit `instance/bootstrap.json` to Git (listed in `.gitignore`).

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

#### Option 3 — Direct SQL (PostgreSQL)

```sql
UPDATE users SET is_admin = TRUE WHERE username = 'your_username';
```

Log in again at `/login` — the **Admin** menu appears in the navigation bar.

#### Expose to internet with ngrok (for mobile testing / OAuth)
```bash
# Terminal 1
python app.py

# Terminal 2
ngrok http --domain=your-domain.ngrok-free.dev 5000
```

Update **Google Redirect URI** in Admin to match your ngrok URL.

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
| `ModuleNotFoundError: psycopg2` | PostgreSQL driver missing | `pip install -r requirements.txt` or `python -m pip install psycopg2-binary` |
| `ModuleNotFoundError` (other) | Virtual env not activated | Run `venv\Scripts\activate` (Windows) |
| `could not connect to server` | PostgreSQL not running | Start PostgreSQL service (`postgresql-x64-*`) |
| `password authentication failed` | Wrong user/password | Fix `database_uri` in `instance/bootstrap.json` |
| `database "luanvan_ai" does not exist` | DB not created | Run `database/init_postgres.sql` |
| `relation "users" does not exist` | Schema not created | Run `python init_db.py` |
| `No such client: google` | OAuth not in DB | Run `migrate_env_to_db.py` or configure Admin → Integrations |
| `API key invalid` | Wrong AI key | Admin → Settings → OpenRouter/Gemini key |
| Port 5000 in use | Another app on port 5000 | Stop other app or change port |
| PDF not readable | Scanned/image PDF | Enable OCR in Admin or pre-process PDF |

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
