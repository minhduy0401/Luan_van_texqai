# Hướng Dẫn Cài Đặt TEXTQAI | Installation Guide

> **Phiên bản / Version:** 1.1 &nbsp;|&nbsp; **Cập nhật / Updated:** 06/2026  
> **CSDL / Database:** PostgreSQL 14+ **hoặc** MySQL 8+ / MariaDB 10+ — chọn **một** trong hai ([mục 4](#4-cài-đặt-postgresql) | [mục 5](#5-cài-đặt-mysql--mariadb--xampp))

---

## 🇻🇳 TIẾNG VIỆT

### Mục lục
1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Clone mã nguồn từ GitHub](#2-clone-mã-nguồn-từ-github)
3. [Cài đặt môi trường Python](#3-cài-đặt-môi-trường-python)
4. [Cài đặt PostgreSQL](#4-cài-đặt-postgresql)
5. [Cài đặt MySQL / MariaDB / XAMPP](#5-cài-đặt-mysql--mariadb--xampp)
6. [Cấu trúc database — PK & FK](#6-cấu-trúc-database--pk--fk)
7. [Cấu hình bootstrap](#7-cấu-hình-bootstrap-instancebootstrapjson)
8. [Khởi động ứng dụng](#8-khởi-động-ứng-dụng)
9. [Tạo tài khoản admin](#9-tạo-tài-khoản-admin)
10. [Deploy production (tùy chọn)](#10-deploy-production-tùy-chọn)
11. [Xử lý lỗi thường gặp](#11-xử-lý-lỗi-thường-gặp)
12. [Giao diện đa ngôn ngữ Anh/Việt](#12-giao-diện-đa-ngôn-ngữ-anhviệt)
13. [Công nghệ & tích hợp sử dụng](#13-công-nghệ--tích-hợp-sử-dụng-trong-dự-án)

---

### 1. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|-----------|-------------------|
| Python | 3.10+ |
| Git | 2.30+ |
| PostgreSQL | 14+ — xem [mục 4](#4-cài-đặt-postgresql) |
| MySQL / MariaDB / XAMPP | 8+ / 10+ — xem [mục 5](#5-cài-đặt-mysql--mariadb--xampp) |
| Driver Python | `psycopg2-binary` (PostgreSQL, trong `requirements.txt`) hoặc `mysql-connector-python` (MySQL — cài thêm) |
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

Mở terminal/cmd, chọn thư mục muốn đặt dự án, rồi chạy **một trong hai cách**:

**Cách A — Clone thẳng vào folder đích (khuyến nghị):**

```bash
mkdir TEXTQAI_Setup
cd TEXTQAI_Setup
git clone https://github.com/minhduy0401/Luan_van_texqai.git .
```

**Cách B — Clone tạo folder con:**

```bash
git clone https://github.com/minhduy0401/Luan_van_texqai.git
cd Luan_van_texqai
```

#### Bước 3 – Kiểm tra đúng thư mục project

Trước khi `pip install` hoặc `python app.py`, terminal phải nằm **cùng folder với `app.py` và `requirements.txt`**:

```bash
# Windows
dir app.py
dir requirements.txt

# macOS / Linux
ls app.py requirements.txt
```

| Triệu chứng | Nguyên nhân | Cách xử lý |
|-------------|-------------|------------|
| `No such file or directory: requirements.txt` | Đang ở folder cha (chỉ thấy `Luan_van_texqai/` bên trong) | `cd Luan_van_texqai` hoặc clone lại với dấu `.` (Cách A) |
| VS Code/Cursor mở nhầm folder cha | Terminal IDE sai cwd | **File → Open Folder** → chọn folder có `app.py` |

> Mở project bằng VS Code/Cursor: chọn folder **có trực tiếp** `app.py`, không phải folder bọc ngoài.

#### Bước 4 – (Tùy chọn) Cập nhật code sau này
Khi repository có phiên bản mới:

```bash
git pull
```

> 💡 Nếu dùng SSH: `git clone git@github.com:minhduy0401/Luan_van_texqai.git`

---

### 3. Cài đặt môi trường Python

> Chạy các lệnh dưới đây **trong folder project** (có `app.py`) — xem [mục 2 bước 3](#bước-3--kiểm-tra-đúng-thư-mục-project).

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
> **MySQL:** sau bước này chạy thêm `pip install mysql-connector-python` ([mục 5](#5-cài-đặt-mysql--mariadb--xampp)).

---

### 4. Cài đặt PostgreSQL

TEXTQAI kết nối PostgreSQL qua SQLAlchemy URI `postgresql+psycopg2://...`. Chọn **mục 4** hoặc **[mục 5](#5-cài-đặt-mysql--mariadb--xampp)** — không cần cài cả hai.

#### Bước 1 – Cài PostgreSQL

| Nền tảng | Lệnh / Link |
|----------|-------------|
| **Windows** | [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) hoặc `winget install PostgreSQL.PostgreSQL.17` |
| **Ubuntu / Debian** | `sudo apt update && sudo apt install postgresql postgresql-contrib` |
| **macOS** | `brew install postgresql@16 && brew services start postgresql@16` |
| **Docker** | `docker run -d --name textqai-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16` |

Ghi nhớ mật khẩu user **`postgres`** khi cài.

#### Bước 2 – Tạo database và user

File: `database/init_postgres.sql`

> **Tên database:** hướng dẫn này dùng `textqai`. File SQL trong repo mặc định là `luanvan_ai` — mở file, Find & Replace `luanvan_ai` → `textqai` trước khi chạy.

```bash
psql -U postgres -f database/init_postgres.sql
psql -U postgres -d textqai -c "GRANT ALL ON SCHEMA public TO textqai_user;"
psql -U postgres -d textqai -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO textqai_user;"
```

> **Windows:** nếu không có `psql` trong PATH:  
> `"D:\PostgresSQL\bin\psql.exe" -U postgres -f database\init_postgres.sql`

| Thành phần | Giá trị mặc định |
|------------|------------------|
| Database | `textqai` (UTF8) |
| User app | `textqai_user` / mật khẩu `your_password` (sửa trong file SQL trước khi chạy) |
| User dev | `postgres` — có thể dùng trực tiếp trong `bootstrap.json` |

#### Bước 3 – Cài driver Python

Driver PostgreSQL đã có trong `requirements.txt`:

```bash
pip install -r requirements.txt
# hoặc riêng: pip install psycopg2-binary
```

#### Bước 4 – Thông tin kết nối

```
Host:     127.0.0.1
Port:     5432
Database: textqai
User:     postgres hoặc textqai_user
Password: (mật khẩu đã đặt)
```

#### Bước 5 – Cấu hình `instance/bootstrap.json`

```bash
python setup_bootstrap.py
```

Sửa URI PostgreSQL:

```json
{
  "database_uri": "postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/textqai",
  "secret_key": "your-secret-key-change-this"
}
```

> Mật khẩu có ký tự đặc biệt (`@`, `#`, `%`…) phải [URL-encode](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls).

#### Bước 6 – Tạo bảng (schema + PK/FK)

**Cách A — Python (tự seed `system_settings`):**

```bash
python init_db.py
```

**Cách B — SQL thuần (12 bảng, đủ khóa chính & khóa ngoại):**

```bash
psql -U postgres -d textqai -f database/schema_postgres.sql
python init_db.py
```

> Chạy `init_db.py` sau Cách B để seed gói giá và cài đặt mặc định vào `system_settings`.

Chi tiết cột, PK, FK: [mục 6](#6-cấu-trúc-database--pk--fk).

---

### 5. Cài đặt MySQL / MariaDB / XAMPP

TEXTQAI kết nối MySQL qua SQLAlchemy URI `mysql+mysqlconnector://...`. Cùng tên database **`textqai`** như PostgreSQL.

#### Bước 1 – Cài MySQL / MariaDB

| Nền tảng | Cách cài |
|----------|----------|
| **XAMPP (Windows/macOS/Linux)** | [apachefriends.org](https://www.apachefriends.org/) → bật **MySQL** trong Control Panel |
| **MySQL 8+** | [dev.mysql.com/downloads](https://dev.mysql.com/downloads/mysql/) |
| **MariaDB 10+** | [mariadb.org/download](https://mariadb.org/download/) — URI giống MySQL |
| **Docker MySQL** | `docker run -d --name textqai-mysql -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=textqai -p 3306:3306 mysql:8` |
| **Docker MariaDB** | `docker run -d --name textqai-mdb -e MARIADB_ROOT_PASSWORD=root -e MARIADB_DATABASE=textqai -p 3306:3306 mariadb:11` |

#### Bước 2 – Tạo database và user

##### XAMPP (Windows — khuyến nghị cho người mới)

1. XAMPP Control Panel → **Start** MySQL (màu xanh)
2. Mở `http://localhost/phpmyadmin` → tab **SQL**
3. Chạy **chỉ** lệnh tạo database (XAMPP dev dùng `root`, không cần `CREATE USER`):

```sql
CREATE DATABASE IF NOT EXISTS textqai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

4. Kiểm tra sidebar trái đã có database `textqai`

> **Lỗi `#1034 - Index for table 'global_priv' is corrupt`** khi chạy `CREATE USER`: do bảng hệ thống XAMPP hỏng — **bỏ qua** `CREATE USER`, chỉ tạo database như trên, dùng `root` trong `bootstrap.json` ([mục 7](#7-cấu-hình-bootstrap-instancebootstrapjson)).

##### MySQL / MariaDB cài riêng (hoặc Docker)

File: `database/init_mysql.sql`

> **Tên database:** hướng dẫn này dùng `textqai`. File SQL trong repo mặc định là `luanvan_ai` — mở file, Find & Replace `luanvan_ai` → `textqai` trước khi chạy.

```bash
mysql -u root -p < database/init_mysql.sql
```

**XAMPP (lệnh terminal, tùy chọn):**

```powershell
"C:\xampp\mysql\bin\mysql.exe" -u root -p < database\init_mysql.sql
```

**phpMyAdmin (file đầy đủ):** dán nội dung `database/init_mysql.sql` → Execute — nếu lỗi `CREATE USER`, dùng khối SQL ngắn ở trên.

| Thành phần | Giá trị mặc định |
|------------|------------------|
| Database | `textqai` (utf8mb4_unicode_ci) |
| User app | `textqai_user` / `your_password` (chỉ khi chạy được `init_mysql.sql` đầy đủ) |
| User dev XAMPP | `root` — thường không mật khẩu (**khuyên dùng**) |

#### Bước 3 – Cài driver Python

Driver MySQL **cài thêm** (không có trong `requirements.txt` mặc định):

```bash
pip install mysql-connector-python
```

#### Bước 4 – Thông tin kết nối

```
Host:     127.0.0.1
Port:     3306
Database: textqai
User:     textqai_user hoặc root
Password: (mật khẩu đã đặt; XAMPP root thường để trống)
Charset:  utf8mb4
```

#### Bước 5 – Cấu hình `instance/bootstrap.json`

Chi tiết đầy đủ: [mục 7](#7-cấu-hình-bootstrap-instancebootstrapjson). **XAMPP (khuyến nghị):**

```json
{
  "database_uri": "mysql+mysqlconnector://root@127.0.0.1:3306/textqai",
  "secret_key": "your-secret-key-change-this"
}
```

| Trường hợp | URI mẫu |
|------------|---------|
| XAMPP `root` không mật khẩu | `mysql+mysqlconnector://root@127.0.0.1:3306/textqai` |
| User + mật khẩu | `mysql+mysqlconnector://textqai_user:your_password@127.0.0.1:3306/textqai` |

#### Bước 6 – Tạo bảng (schema + PK/FK)

> Cần đã lưu `instance/bootstrap.json` trước khi chạy.

**Cách A — Python (seed mặc định, khuyến nghị):**

```bash
python init_db.py
```

**Cách B — SQL thuần:**

```bash
mysql -u root -p textqai < database/schema_mysql.sql
python init_db.py
```

**Nâng cấp schema MySQL rất cũ** (bảng `users` còn cột `password`, thiếu `user_auth_providers`):

```bash
python migrate_db.py
```

> `migrate_db.py` chỉ chạy khi URI bắt đầu bằng `mysql`.

Chi tiết cột, PK, FK: [mục 6](#6-cấu-trúc-database--pk--fk).

---

### 6. Cấu trúc database — PK & FK

TEXTQAI có **12 bảng**. Schema đồng bộ giữa PostgreSQL và MySQL; nguồn chuẩn: `models.py`.

| # | Bảng | Khóa chính (PK) | Mô tả |
|---|------|-----------------|-------|
| 1 | `users` | `id` | Tài khoản người dùng |
| 2 | `user_auth_providers` | `id` | Đăng nhập local / Google |
| 3 | `documents` | `id` | PDF đã upload |
| 4 | `qa_results` | `id` | Câu hỏi–đáp án đã sinh |
| 5 | `agent1_evaluation_logs` | `id` | Log Agent 1 (trích xuất) |
| 6 | `agent2_evaluation_logs` | `id` | Log Agent 2 (lập kế hoạch) |
| 7 | `agent3_evaluation_logs` | `id` | Log Agent 3 (sinh & đánh giá) |
| 8 | `credit_packages` | `id` | Gói mua credit lẻ |
| 9 | `subscription_packages` | `id` | Gói thuê bao tháng |
| 10 | `transactions` | `id` | Lịch sử thanh toán |
| 11 | `feedbacks` | `id` | Phản hồi landing |
| 12 | `system_settings` | `key` | Cấu hình admin (key-value) |

**File SQL đầy đủ:** `database/schema_postgres.sql` | `database/schema_mysql.sql`

#### Sơ đồ quan hệ (ER)

```mermaid
erDiagram
    users ||--o{ user_auth_providers : "user_id FK CASCADE"
    users ||--o{ documents : "user_id FK SET NULL"
    users ||--o{ qa_results : "user_id FK SET NULL"
    users ||--o{ transactions : "user_id FK CASCADE"
    users ||--o{ feedbacks : "user_id FK SET NULL"
    users ||--o{ agent1_evaluation_logs : "user_id FK SET NULL"
    users ||--o{ agent2_evaluation_logs : "user_id FK SET NULL"
    users ||--o{ agent3_evaluation_logs : "user_id FK SET NULL"
    documents ||--o{ qa_results : "document_id FK SET NULL"
    documents ||--o{ agent1_evaluation_logs : "document_id FK SET NULL"
    documents ||--o{ agent2_evaluation_logs : "document_id FK SET NULL"
    documents ||--o{ agent3_evaluation_logs : "document_id FK SET NULL"
    credit_packages ||--o{ transactions : "package_id FK SET NULL"
    subscription_packages ||--o{ transactions : "sub_package_id FK SET NULL"
```

#### Bảng khóa ngoại (Foreign Key)

| Bảng con | Cột FK | Tham chiếu | ON DELETE |
|----------|--------|------------|-----------|
| `user_auth_providers` | `user_id` | `users(id)` | **CASCADE** |
| `documents` | `user_id` | `users(id)` | SET NULL |
| `qa_results` | `user_id` | `users(id)` | SET NULL |
| `qa_results` | `document_id` | `documents(id)` | SET NULL |
| `agent1_evaluation_logs` | `user_id` | `users(id)` | SET NULL |
| `agent1_evaluation_logs` | `document_id` | `documents(id)` | SET NULL |
| `agent2_evaluation_logs` | `user_id` | `users(id)` | SET NULL |
| `agent2_evaluation_logs` | `document_id` | `documents(id)` | SET NULL |
| `agent3_evaluation_logs` | `user_id` | `users(id)` | SET NULL |
| `agent3_evaluation_logs` | `document_id` | `documents(id)` | SET NULL |
| `transactions` | `user_id` | `users(id)` | **CASCADE** |
| `transactions` | `package_id` | `credit_packages(id)` | SET NULL |
| `transactions` | `sub_package_id` | `subscription_packages(id)` | SET NULL |
| `feedbacks` | `user_id` | `users(id)` | SET NULL |

#### Ràng buộc UNIQUE (ngoài PK)

| Bảng | Cột / Ràng buộc |
|------|-----------------|
| `users` | `username` UNIQUE, `email` UNIQUE |
| `user_auth_providers` | `UNIQUE(provider, provider_user_id)` — tên constraint: `uq_provider_user` |
| `transactions` | `order_code` UNIQUE |

#### Chi tiết từng bảng

**`users`**

| Cột | Kiểu | PK/FK/UNIQUE | Ghi chú |
|-----|------|--------------|---------|
| `id` | INTEGER | **PK** | Auto increment |
| `username` | VARCHAR(100) | UNIQUE | Nullable (user Google có thể không có) |
| `email` | VARCHAR(255) | UNIQUE | Nullable |
| `display_name` | VARCHAR(255) | | |
| `is_active` | BOOLEAN | NOT NULL DEFAULT TRUE | |
| `is_admin` | BOOLEAN | NOT NULL DEFAULT FALSE | |
| `credits` | INTEGER | NOT NULL DEFAULT 5 | |
| `created_at` | TIMESTAMP | DEFAULT now | |
| `terms_agreed_at` | TIMESTAMP | | NULL = chưa đồng ý điều khoản |

**`user_auth_providers`**

| Cột | Kiểu | PK/FK/UNIQUE | Ghi chú |
|-----|------|--------------|---------|
| `id` | INTEGER | **PK** | |
| `user_id` | INTEGER | **FK → users.id** | NOT NULL |
| `provider` | VARCHAR(50) | | `'local'` \| `'google'` |
| `provider_user_id` | VARCHAR(255) | UNIQUE kết hợp | Google `sub` |
| `provider_email` | VARCHAR(255) | | |
| `password_hash` | VARCHAR(255) | | Chỉ provider `local` |
| `created_at` | TIMESTAMP | | |

**`documents`**

| Cột | Kiểu | PK/FK | Ghi chú |
|-----|------|-------|---------|
| `id` | INTEGER | **PK** | |
| `title` | VARCHAR(255) | NOT NULL | |
| `filename` | VARCHAR(255) | | |
| `content` | TEXT | | Nội dung PDF trích xuất |
| `upload_date` | TIMESTAMP | | |
| `user_id` | INTEGER | **FK → users.id** | |

**`qa_results`**

| Cột | Kiểu | PK/FK | Ghi chú |
|-----|------|-------|---------|
| `id` | INTEGER | **PK** | |
| `content`, `question`, `answer` | TEXT | | |
| `bloom_level`, `algorithm` | VARCHAR(50) | | |
| `process_time` | FLOAT | | |
| `section_mapping` | VARCHAR(500) | | |
| `total_points` | FLOAT | DEFAULT 0 | |
| `sub_points_count` | INTEGER | DEFAULT 0 | |
| `points_breakdown` | TEXT | | |
| `batch_id` | VARCHAR(20) | | Nhóm lần sinh YYYYMMDDHHMMSS |
| `user_id` | INTEGER | **FK → users.id** | |
| `document_id` | INTEGER | **FK → documents.id** | |

**`agent1_evaluation_logs` / `agent2_evaluation_logs` / `agent3_evaluation_logs`**

| Cột chung | PK/FK |
|-----------|-------|
| `id` | **PK** |
| `request_id` | NOT NULL |
| `user_id` | **FK → users.id** |
| `document_id` | **FK → documents.id** |
| `decision`, `reasons_json`, `quality_score`, `created_at` | Log đánh giá pipeline |

Agent 3 thêm: `target_bloom`, `generated_bloom`, `validated_bloom`, `bloom_match_type`, `source_faithfulness_score`, `scoreability_score`.

**`credit_packages` / `subscription_packages`** — PK `id`; không có FK đi ra.

**`transactions`**

| Cột | PK/FK/UNIQUE |
|-----|--------------|
| `id` | **PK** |
| `user_id` | **FK → users.id** NOT NULL |
| `package_id` | **FK → credit_packages.id** |
| `sub_package_id` | **FK → subscription_packages.id** |
| `order_code` | **UNIQUE** NOT NULL |
| `amount_vnd`, `credits_added` | NOT NULL |
| `status` | DEFAULT `'pending'` |
| `payment_method`, `payos_data`, `created_at`, `paid_at` | |

**`feedbacks`** — PK `id`; FK `user_id → users.id` (nullable).

**`system_settings`** — PK `key` (VARCHAR 100); `value` TEXT NOT NULL.

---

### 7. Cấu hình bootstrap (`instance/bootstrap.json`)

App chỉ cần **một file bootstrap** để biết cách kết nối DB lần đầu. **Không dùng `.env`** cho database URI.

> ⚠️ **`database_uri` là nội dung file JSON** — mở `instance/bootstrap.json` trong editor, sửa và **Ctrl+S lưu**. **Không** gõ/paste chuỗi `mysql+mysqlconnector://...` vào PowerShell/CMD (đó không phải lệnh terminal).

#### Bước 1 – Tạo file bootstrap

```bash
python setup_bootstrap.py
```

#### Bước 2 – Sửa `instance/bootstrap.json`

**PostgreSQL:**

```json
{
  "database_uri": "postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/textqai",
  "secret_key": "your-secret-key-change-this"
}
```

**MySQL / XAMPP (khuyến nghị dev local):**

```json
{
  "database_uri": "mysql+mysqlconnector://root@127.0.0.1:3306/textqai",
  "secret_key": "a8fK2mP9xQ7vL4nR1wT6yU3zB0cD5eG8"
}
```

| Trường | Ý nghĩa |
|--------|---------|
| `database_uri` | Chuỗi kết nối SQLAlchemy — PostgreSQL: [mục 4](#4-cài-đặt-postgresql) · MySQL: [mục 5](#5-cài-đặt-mysql--mariadb--xampp). Tên database phải khớp bước tạo DB (`textqai`). |
| `secret_key` | Chuỗi bí mật **tự đặt** cho Flask mã hóa session đăng nhập — **không phải** API key AI. Dev: chuỗi dài bất kỳ; production: random mạnh, không commit Git. |

> Mật khẩu DB có ký tự đặc biệt (`@`, `#`, `%`…) phải [URL-encode](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls) trong URI.

#### Bước 3 – Tạo bảng (nếu chưa chạy)

```bash
python init_db.py
```

Tạo 12 bảng + seed `system_settings`. Chỉ chạy **sau** khi `bootstrap.json` đã lưu đúng.

#### Bước 4 – Cấu hình còn lại qua Admin

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

### 8. Khởi động ứng dụng

#### Development (phát triển local)
```bash
python app.py
```
Truy cập: `http://localhost:5000`

---

### 9. Tạo tài khoản admin

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

#### Cách 3 — SQL trực tiếp (PostgreSQL hoặc MySQL)

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
ngrok http --domain=lining-unaired-catwalk.ngrok-free.dev 5000
```

Cập nhật **Google Redirect URI** trong Admin cho khớp URL ngrok.

---

### 10. Deploy production (tùy chọn)

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

### 11. Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| `No such file or directory: requirements.txt` | Terminal sai folder (folder cha, không có `app.py`) | `cd` vào folder có `app.py`; hoặc clone với dấu `.` ([mục 2](#2-clone-mã-nguồn-từ-github)) |
| `The term 'mysql+mysqlconnector://…' is not recognized` | Gõ URI vào PowerShell thay vì file JSON | Ghi URI vào `instance/bootstrap.json`, lưu file, rồi `python init_db.py` |
| `#1034 global_priv corrupt` (CREATE USER) | Bảng hệ thống XAMPP hỏng | Chỉ `CREATE DATABASE textqai` trong phpMyAdmin; dùng `root` trong bootstrap |
| `ModuleNotFoundError: psycopg2` | Chưa cài driver PostgreSQL | `pip install -r requirements.txt` hoặc `python -m pip install psycopg2-binary` |
| `No module named 'mysql'` / `mysql.connector` | Dùng MySQL nhưng thiếu driver | `pip install mysql-connector-python` |
| `ModuleNotFoundError` (khác) | Chưa kích hoạt venv | `venv\Scripts\activate` (Windows) |
| `could not connect to server` | PostgreSQL chưa chạy | Khởi động service PostgreSQL (Services → `postgresql-x64-*`) |
| `Can't connect to MySQL server` | MySQL/XAMPP chưa chạy | Bật MySQL trong XAMPP Control Panel hoặc service MySQL |
| `Access denied for user` (MySQL) | Sai user/mật khẩu | Kiểm tra URI trong `bootstrap.json`; XAMPP dev thường dùng `root` không mật khẩu |
| `Unknown database 'textqai'` | Chưa tạo DB | PostgreSQL: `init_postgres.sql` · MySQL: `init_mysql.sql` |
| `password authentication failed` | Sai mật khẩu / user | Sửa `database_uri` trong `instance/bootstrap.json` |
| `database "textqai" does not exist` | Chưa tạo DB | Chạy `database/init_postgres.sql` |
| `relation "users" does not exist` | Chưa tạo bảng | Chạy `python init_db.py` |
| `No such client: google` | OAuth chưa có trong DB | Chạy `migrate_env_to_db.py` hoặc cấu hình Admin → Tích hợp |
| `API key invalid` | Key AI chưa đúng | Admin → Cài đặt → nhập OpenRouter/Gemini key |
| Port 5000 đang dùng | Có app khác chiếm cổng | Dừng app cũ hoặc đổi port |
| PDF không đọc được | File PDF là ảnh scan | Bật OCR trong Admin hoặc OCR trước khi upload |

---

### 12. Giao diện đa ngôn ngữ (Anh/Việt)

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

### 13. Công nghệ & tích hợp sử dụng trong dự án

Bảng dưới liệt kê **toàn bộ công nghệ, thư viện và dịch vụ bên thứ ba** mà TEXTQAI sử dụng — kèm vai trò và nơi cấu hình trong Admin (nếu có).

#### 13.1. Nền tảng & Backend

| Công nghệ | Phiên bản / Ghi chú | Vai trò trong dự án |
|-----------|---------------------|---------------------|
| **Python** | 3.10+ | Ngôn ngữ chính |
| **Flask** | 3.x (`requirements.txt`) | Web framework, routing, template |
| **Werkzeug** | 3.x | HTTP utilities, hash mật khẩu, upload file |
| **Waitress** | 3.x | WSGI server production (thay Flask dev server) |
| **Flask-Login** | 0.6.x | Phiên đăng nhập, `remember_me`, `@login_required` |
| **Flask-SQLAlchemy** | 3.x | ORM tích hợp Flask |
| **SQLAlchemy** | 2.x | Truy vấn DB, migration schema qua model |
| **ProxyFix** (Werkzeug) | — | Đọc header HTTPS/host từ ngrok / Nginx reverse proxy |
| **Jinja2** | (kèm Flask) | Template HTML server-side |

**File liên quan:** `app.py`, `extensions.py`, `models.py`

---

#### 13.2. Cơ sở dữ liệu

| Công nghệ | Vai trò | Cấu hình |
|-----------|---------|----------|
| **PostgreSQL** | 14+ | [mục 4](#4-cài-đặt-postgresql) · schema: `schema_postgres.sql` |
| **MySQL / MariaDB** | 8+ / 10+ | [mục 5](#5-cài-đặt-mysql--mariadb--xampp) · schema: `schema_mysql.sql` |
| **Cấu trúc PK/FK** | 12 bảng | [mục 6](#6-cấu-trúc-database--pk--fk) |
| **psycopg2-binary** | Driver Python ↔ PostgreSQL | `requirements.txt` |
| **mysql-connector-python** | Driver Python ↔ MySQL | `pip install mysql-connector-python` |
| **Bảng `system_settings`** | Key-value cấu hình runtime (API key, OAuth, SMTP…) | Admin → Cài đặt |
| **Bảng `users`, `documents`, `qa_results`** | Tài khoản, PDF, câu hỏi sinh ra | Tự tạo qua `init_db.py` |
| **Bảng `credit_packages`, `subscription_packages`, `transactions`** | Gói giá & lịch sử thanh toán | Admin → Cài đặt → Quản lý gói |
| **Bảng `user_auth_providers`** | Liên kết tài khoản Google OAuth | Tự động khi đăng nhập Google |

**File liên quan:** `database/init_postgres.sql`, `init_db.py`, `models.py`

---

#### 13.3. Giao diện người dùng (Frontend)

| Công nghệ | Nguồn | Vai trò |
|-----------|-------|---------|
| **Bootstrap 5.3** | CDN jsDelivr | Layout responsive, component UI |
| **Bootstrap Icons** | CDN | Icon navbar, admin, form |
| **Chart.js** | `static/js/chart.umd.min.js` | Biểu đồ tròn/cột trong Admin (Bloom, thuật toán, doanh thu) |
| **Google Fonts** | CDN | Inter, Manrope, Space Grotesk |
| **HTML / CSS / JavaScript thuần** | `templates/`, inline JS | Landing, index, export PDF, accordion Q&A |
| **i18n tự viết** | `utils/translations.py` | Song ngữ Vi/En — xem [mục 12](#12-giao-diện-đa-ngôn-ngữ-anhviệt) |

**File liên quan:** `templates/base.html`, `templates/admin/`, `templates/landing.html`

---

#### 13.4. Trí tuệ nhân tạo (AI / LLM)

| Công nghệ | Vai trò | Cấu hình Admin |
|-----------|---------|----------------|
| **OpenAI Python SDK** | Client thống nhất gọi chat/completions | — |
| **OpenRouter** | Gateway LLM (Gemini, Claude, GPT… qua một API) | API key + model → **Cấu hình model AI** |
| **Google Gemini API** | Gọi trực tiếp qua endpoint OpenAI-compatible | Gemini API key + model |
| **OpenAI API** | Gọi trực tiếp GPT | OpenAI API key + model |
| **Pipeline 3 tác nhân** | Trích xuất PDF → sinh Q&A → đánh giá chất lượng | Model AI đang kích hoạt |
| **Thang Bloom (6 cấp)** | Phân loại câu hỏi Nhớ → Sáng tạo | `utils/bloom.py`, form sinh đề |

**File liên quan:** `services/pipeline.py`, `extensions.py` (`DynamicAIClient`), `config.py`

> 💡 Chỉ cần **một** nhà cung cấp AI đang active; đổi provider không cần sửa code.

---

#### 13.5. Xử lý PDF & OCR

| Công nghệ | Vai trò | Ghi chú |
|-----------|---------|---------|
| **pdfplumber** | Trích xuất text từ PDF text-based | Mặc định |
| **PyMuPDF (fitz)** | Đọc PDF, render trang ảnh | Hỗ trợ pipeline |
| **Pillow (PIL)** | Xử lý ảnh trang PDF | OCR preprocessing |
| **pytesseract** | OCR qua Tesseract | Cần cài **Tesseract OCR** trên hệ thống |
| **RapidOCR (ONNX)** | OCR fallback không cần Tesseract | `rapidocr-onnxruntime` |
| **numpy** | Xử lý mảng ảnh cho OCR | Kèm RapidOCR |

**Cấu hình:** Admin → **Bật OCR** (`enable_ocr` trong `system_settings`)

**File liên quan:** `services/pdf.py`, `services/pipeline.py`

---

#### 13.6. Xác thực, bảo mật & chống spam

| Công nghệ | Loại | Vai trò | Cấu hình Admin |
|-----------|------|---------|----------------|
| **Đăng nhập email/mật khẩu** | Nội bộ | Werkzeug `generate_password_hash` / `check_password_hash` | — |
| **Google OAuth 2.0 / OpenID Connect** | Bên thứ ba | Đăng nhập bằng tài khoản Google | **Tích hợp** → Client ID, Secret, Redirect URI |
| **Authlib** | Thư viện Python | Client OAuth Flask, metadata Google OIDC | — |
| **Google reCAPTCHA v2** | Bên thứ ba | Checkbox “Tôi không phải robot” | **Bảo mật** → Site Key + Secret Key |
| **Google reCAPTCHA v3** | Bên thứ ba | Invisible score-based (login/register) | `captcha_type` = `v3` |
| **Captcha Gate** | Nội bộ | Trang xác minh bổ sung khi nghi ngờ bot | Route `/captcha-gate` |
| **Flask Session + Secret Key** | Nội bộ | Cookie phiên, CSRF cơ bản | `bootstrap.json` / Admin → Secret Key |
| **Quên mật khẩu** | Nội bộ + SMTP | Gửi mật khẩu tạm qua email | Bật trong **Bảo mật** + cấu hình SMTP |

**File liên quan:** `app.py` (`/auth/google`, `verify_captcha`), `templates/login.html`, `templates/register.html`

---

#### 13.7. Email (SMTP)

| Công nghệ | Vai trò | Cấu hình Admin |
|-----------|---------|----------------|
| **smtplib** (Python chuẩn) | Gửi email qua SMTP TLS | **Bảo mật** → Máy chủ SMTP |
| **Gmail / Outlook / SMTP riêng** | Nhà cung cấp mail | Server, Port (587), User, App Password |

**Dùng cho:** quên mật khẩu, thông báo đơn hàng pending/thành công.

**File liên quan:** `app.py` → `send_email_smtp()`

---

#### 13.8. Thanh toán & nạp credits

| Công nghệ | Loại | Vai trò | Cấu hình Admin |
|-----------|------|---------|----------------|
| **Chuyển khoản ngân hàng (thủ công)** | Nội bộ | Tạo đơn `pending`, admin duyệt hoặc chờ webhook | **Thanh toán** → Tên NH, STK, chủ TK |
| **VietQR (img.vietqr.io)** | API ảnh QR | Hiển thị mã QR chuyển khoản | BIN ngân hàng + số TK |
| **SePay** | Bên thứ ba | Webhook tự động xác nhận chuyển khoản, cộng credits | API Key + Webhook URL |
| **VNPAY** | Cổng thanh toán VN | Thanh toán thẻ/QR qua sandbox hoặc production | TMN Code, Hash Secret, Return URL |
| **HMAC SHA512** | Thuật toán | Ký & verify giao dịch VNPAY | `services/payment.py` |

**Luồng credits:** `Transaction` → `status=paid` → cộng `users.credits`.

**File liên quan:** `services/payment.py`, `app.py` (`/payment/create`, `/payment/vnpay/*`, `/payment/sepay/webhook`), `docs/vnpay_integration.md`

---

#### 13.9. Quản trị & cấu hình hệ thống

| Thành phần | Vai trò |
|------------|---------|
| **Admin Panel** | Dashboard, user, giao dịch, thống kê, phản hồi, cài đặt |
| **`instance/bootstrap.json`** | DB URI + secret key ban đầu (không commit Git) |
| **`system_settings` (DB)** | Toàn bộ cấu hình runtime sau khi deploy |
| **Site Shell / Branding** | Logo, favicon, tên site, SEO title/description, Open Graph |
| **`migrate_env_to_db.py`** | Import một lần từ `.env` cũ sang DB |
| **`create_admin.py`** | Tạo/nâng quyền tài khoản admin CLI |

---

#### 13.10. Xuất dữ liệu & thí nghiệm

| Công nghệ | Vai trò |
|-----------|---------|
| **ReportLab** | Xuất đề kiểm tra / Q&A ra file PDF |
| **NLTK** | Thí nghiệm đánh giá độ chính xác Bloom (`experiment/`) |

**File liên quan:** `app.py` (route export PDF), `experiment/experiment_2_bloom_accuracy.py`

---

#### 13.11. Triển khai & môi trường dev

| Công nghệ | Vai trò |
|-----------|---------|
| **Git / GitHub** | Quản lý mã nguồn |
| **ngrok** | Expose localhost ra HTTPS (test OAuth, mobile, demo) |
| **Waitress** | Chạy production trên Windows/Linux |
| **Docker** (tùy chọn) | Container PostgreSQL |

---

#### 13.12. Tóm tắt — cấu hình qua Admin

| Nhóm | Mục trong Admin → Cài đặt | Dịch vụ bên thứ ba |
|------|---------------------------|-------------------|
| AI | Cấu hình model AI | OpenRouter, Gemini, OpenAI |
| Tích hợp | OAuth, VNPAY, SePay, Secret Key | Google, VNPAY, SePay |
| Thanh toán | Ngân hàng, BIN VietQR | VietQR API |
| Bảo mật | reCAPTCHA, SMTP, quên MK | Google reCAPTCHA, Gmail SMTP |
| Giao diện | Site Shell / Branding | — (upload file local) |
| Gói giá | Credit lẻ + Thuê bao | — (lưu DB) |

> 📌 **Nguyên tắc cấu hình:** chỉ `bootstrap.json` cần file local để khởi động lần đầu; **mọi secret và tích hợp khác** nên cấu hình qua **Admin → Cài đặt** (lưu CSDL — PostgreSQL hoặc MySQL), không hardcode trong mã nguồn.

---
---

## 🇬🇧 ENGLISH

### Table of Contents
1. [System Requirements](#1-system-requirements)
2. [Clone Source from GitHub](#2-clone-source-from-github)
3. [Set Up Python Environment](#3-set-up-python-environment)
4. [Set Up PostgreSQL Database](#4-set-up-postgresql-database)
5. [Set Up MySQL / MariaDB / XAMPP](#5-set-up-mysql--mariadb--xampp)
6. [Database Schema — PK & FK](#6-database-schema--pk--fk)
7. [Bootstrap config](#7-bootstrap-config-instancebootstrapjson)
8. [Start the Application](#8-start-the-application)
9. [Create Admin Account](#9-create-admin-account)
10. [Production Deployment (Optional)](#10-production-deployment-optional)
11. [Troubleshooting](#11-troubleshooting)
12. [Bilingual UI (English/Vietnamese)](#12-bilingual-ui-englishvietnamese)
13. [Technologies & Integrations](#13-technologies--integrations-used-in-the-project)

---

### 1. System Requirements

| Component | Minimum Version |
|-----------|----------------|
| Python | 3.10+ |
| Git | 2.30+ |
| PostgreSQL | 14+ — see [Section 4](#4-set-up-postgresql-database) |
| MySQL / MariaDB / XAMPP | 8+ / 10+ — see [Section 5](#5-set-up-mysql--mariadb--xampp) |
| Python driver | `psycopg2-binary` (PostgreSQL, in `requirements.txt`) or `mysql-connector-python` (MySQL — install separately) |
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

Open a terminal, navigate to your desired folder, then use **one of these approaches**:

**Option A — Clone directly into target folder (recommended):**

```bash
mkdir TEXTQAI_Setup
cd TEXTQAI_Setup
git clone https://github.com/minhduy0401/Luan_van_texqai.git .
```

**Option B — Clone into a subfolder:**

```bash
git clone https://github.com/minhduy0401/Luan_van_texqai.git
cd Luan_van_texqai
```

#### Step 3 – Verify project directory

Before `pip install` or `python app.py`, your terminal must be **in the same folder as `app.py` and `requirements.txt`**:

```bash
# Windows
dir app.py
dir requirements.txt

# macOS / Linux
ls app.py requirements.txt
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No such file or directory: requirements.txt` | Parent folder (only `Luan_van_texqai/` inside) | `cd Luan_van_texqai` or re-clone with `.` (Option A) |
| VS Code/Cursor opened parent folder | IDE terminal wrong cwd | **File → Open Folder** → pick folder containing `app.py` |

> Open the project in VS Code/Cursor: select the folder that **directly contains** `app.py`, not the outer wrapper.

#### Step 4 – (Optional) Pull updates later
When new code is pushed to the repository:

```bash
git pull
```

> 💡 For SSH: `git clone git@github.com:minhduy0401/Luan_van_texqai.git`

---

### 3. Set Up Python Environment

> Run commands below **inside the project folder** (where `app.py` lives) — see [Section 2 Step 3](#step-3--verify-project-directory).

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
> **MySQL:** also run `pip install mysql-connector-python` afterward ([Section 5](#5-set-up-mysql--mariadb--xampp)).

---

### 4. Set Up PostgreSQL Database

TEXTQAI connects to PostgreSQL via SQLAlchemy URI `postgresql+psycopg2://...`. Choose **Section 4** or **[Section 5](#5-set-up-mysql--mariadb--xampp)** — you do not need both.

#### Step 1 – Install PostgreSQL

| Platform | Command / Link |
|----------|----------------|
| **Windows** | [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) or `winget install PostgreSQL.PostgreSQL.17` |
| **Ubuntu / Debian** | `sudo apt update && sudo apt install postgresql postgresql-contrib` |
| **macOS** | `brew install postgresql@16 && brew services start postgresql@16` |
| **Docker** | `docker run -d --name textqai-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16` |

Remember the **`postgres`** user password during installation.

#### Step 2 – Create database and user

File: `database/init_postgres.sql`

> **Database name:** this guide uses `textqai`. Repo SQL files default to `luanvan_ai` — open the file and Find & Replace `luanvan_ai` → `textqai` before running.

```bash
psql -U postgres -f database/init_postgres.sql
psql -U postgres -d textqai -c "GRANT ALL ON SCHEMA public TO textqai_user;"
psql -U postgres -d textqai -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO textqai_user;"
```

> **Windows:** if `psql` is not in PATH:  
> `"D:\PostgresSQL\bin\psql.exe" -U postgres -f database\init_postgres.sql`

| Item | Default value |
|------|---------------|
| Database | `textqai` (UTF8) |
| App user | `textqai_user` / password `your_password` (edit SQL file before running) |
| Dev user | `postgres` — may be used directly in `bootstrap.json` |

#### Step 3 – Install Python driver

PostgreSQL driver is included in `requirements.txt`:

```bash
pip install -r requirements.txt
# or alone: pip install psycopg2-binary
```

#### Step 4 – Connection details

```
Host:     127.0.0.1
Port:     5432
Database: textqai
User:     postgres or textqai_user
Password: (password you set)
```

#### Step 5 – Configure `instance/bootstrap.json`

```bash
python setup_bootstrap.py
```

PostgreSQL URI example:

```json
{
  "database_uri": "postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/textqai",
  "secret_key": "your-secret-key-change-this"
}
```

> URL-encode special characters in the password (`@`, `#`, `%`, …).

#### Step 6 – Create tables (schema + PK/FK)

**Option A — Python (seeds `system_settings`):**

```bash
python init_db.py
```

**Option B — Pure SQL (12 tables with PKs and FKs):**

```bash
psql -U postgres -d textqai -f database/schema_postgres.sql
python init_db.py
```

> Run `init_db.py` after Option B to seed default packages and settings.

Full column/PK/FK reference: [Section 6](#6-database-schema--pk--fk).

---

### 5. Set Up MySQL / MariaDB / XAMPP

TEXTQAI connects to MySQL via SQLAlchemy URI `mysql+mysqlconnector://...`. Same database name **`textqai`** as PostgreSQL.

#### Step 1 – Install MySQL / MariaDB

| Platform | Installation |
|----------|--------------|
| **XAMPP (Windows/macOS/Linux)** | [apachefriends.org](https://www.apachefriends.org/) → start **MySQL** in Control Panel |
| **MySQL 8+** | [dev.mysql.com/downloads](https://dev.mysql.com/downloads/mysql/) |
| **MariaDB 10+** | [mariadb.org/download](https://mariadb.org/download/) — same URI format |
| **Docker MySQL** | `docker run -d --name textqai-mysql -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=textqai -p 3306:3306 mysql:8` |
| **Docker MariaDB** | `docker run -d --name textqai-mdb -e MARIADB_ROOT_PASSWORD=root -e MARIADB_DATABASE=textqai -p 3306:3306 mariadb:11` |

#### Step 2 – Create database and user

##### XAMPP (Windows — recommended for beginners)

1. XAMPP Control Panel → **Start** MySQL (green)
2. Open `http://localhost/phpmyadmin` → **SQL** tab
3. Run **only** the database creation (XAMPP dev uses `root`, no `CREATE USER` needed):

```sql
CREATE DATABASE IF NOT EXISTS textqai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

4. Confirm `textqai` appears in the left sidebar

> **`#1034 - Index for table 'global_priv' is corrupt`** on `CREATE USER`: XAMPP system table issue — **skip** `CREATE USER`, create DB only as above, use `root` in `bootstrap.json` ([Section 7](#7-bootstrap-config-instancebootstrapjson)).

##### Standalone MySQL / MariaDB (or Docker)

File: `database/init_mysql.sql`

> **Database name:** this guide uses `textqai`. Repo SQL files default to `luanvan_ai` — open the file and Find & Replace `luanvan_ai` → `textqai` before running.

```bash
mysql -u root -p < database/init_mysql.sql
```

**XAMPP (terminal, optional):**

```powershell
"C:\xampp\mysql\bin\mysql.exe" -u root -p < database\init_mysql.sql
```

**phpMyAdmin (full file):** paste `database/init_mysql.sql` → Execute — if `CREATE USER` fails, use the short SQL block above.

| Item | Default value |
|------|---------------|
| Database | `textqai` (utf8mb4_unicode_ci) |
| App user | `textqai_user` / `your_password` (only if full `init_mysql.sql` succeeds) |
| XAMPP dev user | `root` — often no password (**recommended**) |

#### Step 3 – Install Python driver

MySQL driver is **not** in default `requirements.txt`:

```bash
pip install mysql-connector-python
```

#### Step 4 – Connection details

```
Host:     127.0.0.1
Port:     3306
Database: textqai
User:     textqai_user or root
Password: (password you set; XAMPP root often empty)
Charset:  utf8mb4
```

#### Step 5 – Configure `instance/bootstrap.json`

Full details: [Section 7](#7-bootstrap-config-instancebootstrapjson). **XAMPP (recommended):**

```json
{
  "database_uri": "mysql+mysqlconnector://root@127.0.0.1:3306/textqai",
  "secret_key": "your-secret-key-change-this"
}
```

| Case | Sample URI |
|------|------------|
| XAMPP passwordless `root` | `mysql+mysqlconnector://root@127.0.0.1:3306/textqai` |
| User + password | `mysql+mysqlconnector://textqai_user:your_password@127.0.0.1:3306/textqai` |

#### Step 6 – Create tables (schema + PK/FK)

> Save `instance/bootstrap.json` before running.

**Option A — Python (seeds defaults, recommended):**

```bash
python init_db.py
```

**Option B — Pure SQL:**

```bash
mysql -u root -p textqai < database/schema_mysql.sql
python init_db.py
```

**Upgrade very old MySQL schema** (legacy `users.password` column, missing `user_auth_providers`):

```bash
python migrate_db.py
```

> `migrate_db.py` only runs when the URI starts with `mysql`.

Full column/PK/FK reference: [Section 6](#6-database-schema--pk--fk).

---

### 6. Database Schema — PK & FK

TEXTQAI has **12 tables**. Schema is aligned between PostgreSQL and MySQL; source of truth: `models.py`.

| # | Table | Primary Key | Description |
|---|-------|-------------|-------------|
| 1 | `users` | `id` | User accounts |
| 2 | `user_auth_providers` | `id` | Local / Google login |
| 3 | `documents` | `id` | Uploaded PDFs |
| 4 | `qa_results` | `id` | Generated Q&A |
| 5 | `agent1_evaluation_logs` | `id` | Agent 1 logs (extraction) |
| 6 | `agent2_evaluation_logs` | `id` | Agent 2 logs (planning) |
| 7 | `agent3_evaluation_logs` | `id` | Agent 3 logs (generation) |
| 8 | `credit_packages` | `id` | Credit packages |
| 9 | `subscription_packages` | `id` | Subscription packages |
| 10 | `transactions` | `id` | Payment history |
| 11 | `feedbacks` | `id` | Landing feedback |
| 12 | `system_settings` | `key` | Admin config (key-value) |

**Full SQL files:** `database/schema_postgres.sql` | `database/schema_mysql.sql`

#### ER diagram

```mermaid
erDiagram
    users ||--o{ user_auth_providers : "user_id FK CASCADE"
    users ||--o{ documents : "user_id FK SET NULL"
    users ||--o{ qa_results : "user_id FK SET NULL"
    users ||--o{ transactions : "user_id FK CASCADE"
    users ||--o{ feedbacks : "user_id FK SET NULL"
    users ||--o{ agent1_evaluation_logs : "user_id FK SET NULL"
    users ||--o{ agent2_evaluation_logs : "user_id FK SET NULL"
    users ||--o{ agent3_evaluation_logs : "user_id FK SET NULL"
    documents ||--o{ qa_results : "document_id FK SET NULL"
    documents ||--o{ agent1_evaluation_logs : "document_id FK SET NULL"
    documents ||--o{ agent2_evaluation_logs : "document_id FK SET NULL"
    documents ||--o{ agent3_evaluation_logs : "document_id FK SET NULL"
    credit_packages ||--o{ transactions : "package_id FK SET NULL"
    subscription_packages ||--o{ transactions : "sub_package_id FK SET NULL"
```

#### Foreign keys

| Child table | FK column | References | ON DELETE |
|-------------|-----------|------------|-----------|
| `user_auth_providers` | `user_id` | `users(id)` | **CASCADE** |
| `documents` | `user_id` | `users(id)` | SET NULL |
| `qa_results` | `user_id` | `users(id)` | SET NULL |
| `qa_results` | `document_id` | `documents(id)` | SET NULL |
| `agent1_evaluation_logs` | `user_id` | `users(id)` | SET NULL |
| `agent1_evaluation_logs` | `document_id` | `documents(id)` | SET NULL |
| `agent2_evaluation_logs` | `user_id` | `users(id)` | SET NULL |
| `agent2_evaluation_logs` | `document_id` | `documents(id)` | SET NULL |
| `agent3_evaluation_logs` | `user_id` | `users(id)` | SET NULL |
| `agent3_evaluation_logs` | `document_id` | `documents(id)` | SET NULL |
| `transactions` | `user_id` | `users(id)` | **CASCADE** |
| `transactions` | `package_id` | `credit_packages(id)` | SET NULL |
| `transactions` | `sub_package_id` | `subscription_packages(id)` | SET NULL |
| `feedbacks` | `user_id` | `users(id)` | SET NULL |

#### UNIQUE constraints (besides PK)

| Table | Column / constraint |
|-------|---------------------|
| `users` | `username` UNIQUE, `email` UNIQUE |
| `user_auth_providers` | `UNIQUE(provider, provider_user_id)` — constraint name: `uq_provider_user` |
| `transactions` | `order_code` UNIQUE |

#### Per-table details

**`users`** — PK `id`; UNIQUE `username`, `email`; columns: `display_name`, `is_active`, `is_admin`, `credits` (default 5), `created_at`, `terms_agreed_at`.

**`user_auth_providers`** — PK `id`; FK `user_id → users.id` NOT NULL; `provider` (`local`|`google`); UNIQUE `(provider, provider_user_id)`.

**`documents`** — PK `id`; FK `user_id → users.id`; `title` NOT NULL, `filename`, `content`, `upload_date`.

**`qa_results`** — PK `id`; FK `user_id`, `document_id`; Bloom/algorithm fields, scoring, `batch_id`.

**`agent1/2/3_evaluation_logs`** — PK `id`; FK `user_id`, `document_id`; pipeline evaluation JSON logs.

**`credit_packages` / `subscription_packages`** — PK `id`; no outgoing FKs.

**`transactions`** — PK `id`; FK `user_id` (NOT NULL), `package_id`, `sub_package_id`; UNIQUE `order_code`.

**`feedbacks`** — PK `id`; FK `user_id` (nullable).

**`system_settings`** — PK `key`; `value` TEXT NOT NULL.

---

### 7. Bootstrap config (`instance/bootstrap.json`)

The app needs **only one bootstrap file** for the initial DB connection. **Do not use `.env`** for the database URI.

> ⚠️ **`database_uri` belongs in the JSON file** — edit `instance/bootstrap.json` in your editor and **save**. Do **not** paste `mysql+mysqlconnector://...` into PowerShell/CMD (that is not a shell command).

#### Step 1 – Create bootstrap file

```bash
python setup_bootstrap.py
```

#### Step 2 – Edit `instance/bootstrap.json`

**PostgreSQL:**

```json
{
  "database_uri": "postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/textqai",
  "secret_key": "your-secret-key-change-this"
}
```

**MySQL / XAMPP (recommended for local dev):**

```json
{
  "database_uri": "mysql+mysqlconnector://root@127.0.0.1:3306/textqai",
  "secret_key": "a8fK2mP9xQ7vL4nR1wT6yU3zB0cD5eG8"
}
```

| Field | Meaning |
|-------|---------|
| `database_uri` | SQLAlchemy connection string — PostgreSQL: [Section 4](#4-set-up-postgresql-database) · MySQL: [Section 5](#5-set-up-mysql--mariadb--xampp). DB name must match creation step (`textqai`). |
| `secret_key` | **Self-chosen** secret for Flask login sessions — **not** an AI API key. Dev: any long string; production: strong random, never commit to Git. |

> URL-encode special characters in the DB password (`@`, `#`, `%`, …) in the URI.

#### Step 3 – Create tables (if not done yet)

```bash
python init_db.py
```

Creates 12 tables + seeds `system_settings`. Run only **after** saving a valid `bootstrap.json`.

#### Step 4 – Configure everything else in Admin

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

### 8. Start the Application

#### Development (local)
```bash
python app.py
```
Access at: `http://localhost:5000`

---

### 9. Create Admin Account

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

#### Option 3 — Direct SQL (PostgreSQL or MySQL)

```sql
UPDATE users SET is_admin = TRUE WHERE username = 'your_username';
```

Log in again at `/login` — the **Admin** menu appears in the navigation bar.

#### Expose to internet with ngrok (for mobile testing / OAuth)
```bash
# Terminal 1
python app.py

# Terminal 2
ngrok http --domain=lining-unaired-catwalk.ngrok-free.dev 5000
```

Update **Google Redirect URI** in Admin to match your ngrok URL.

---

### 10. Production Deployment (Optional)

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

### 11. Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `No such file or directory: requirements.txt` | Wrong folder (parent dir, no `app.py`) | `cd` into folder with `app.py`; or clone with `.` ([Section 2](#2-clone-source-from-github)) |
| `The term 'mysql+mysqlconnector://…' is not recognized` | URI typed in PowerShell instead of JSON file | Put URI in `instance/bootstrap.json`, save, then `python init_db.py` |
| `#1034 global_priv corrupt` (CREATE USER) | Corrupt XAMPP system table | Only `CREATE DATABASE textqai` in phpMyAdmin; use `root` in bootstrap |
| `ModuleNotFoundError: psycopg2` | PostgreSQL driver missing | `pip install -r requirements.txt` or `python -m pip install psycopg2-binary` |
| `No module named 'mysql'` / `mysql.connector` | Using MySQL without driver | `pip install mysql-connector-python` |
| `ModuleNotFoundError` (other) | Virtual env not activated | Run `venv\Scripts\activate` (Windows) |
| `could not connect to server` | PostgreSQL not running | Start PostgreSQL service (`postgresql-x64-*`) |
| `Can't connect to MySQL server` | MySQL/XAMPP not running | Start MySQL in XAMPP Control Panel or MySQL service |
| `Access denied for user` (MySQL) | Wrong user/password | Check URI in `bootstrap.json`; XAMPP dev often uses passwordless `root` |
| `Unknown database 'textqai'` | DB not created | PostgreSQL: `init_postgres.sql` · MySQL: `init_mysql.sql` |
| `password authentication failed` | Wrong user/password | Fix `database_uri` in `instance/bootstrap.json` |
| `database "textqai" does not exist` | DB not created | Run `database/init_postgres.sql` |
| `relation "users" does not exist` | Schema not created | Run `python init_db.py` |
| `No such client: google` | OAuth not in DB | Run `migrate_env_to_db.py` or configure Admin → Integrations |
| `API key invalid` | Wrong AI key | Admin → Settings → OpenRouter/Gemini key |
| Port 5000 in use | Another app on port 5000 | Stop other app or change port |
| PDF not readable | Scanned/image PDF | Enable OCR in Admin or pre-process PDF |

---

### 12. Bilingual UI (English/Vietnamese)

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

---

### 13. Technologies & Integrations Used in the Project

The tables below list **all technologies, libraries, and third-party services** used by TEXTQAI — with their role and Admin configuration location (where applicable).

#### 13.1. Platform & Backend

| Technology | Version / Notes | Role in the project |
|------------|-----------------|----------------------|
| **Python** | 3.10+ | Primary language |
| **Flask** | 3.x (`requirements.txt`) | Web framework, routing, templates |
| **Werkzeug** | 3.x | HTTP utilities, password hashing, file uploads |
| **Waitress** | 3.x | Production WSGI server (replaces Flask dev server) |
| **Flask-Login** | 0.6.x | Login sessions, `remember_me`, `@login_required` |
| **Flask-SQLAlchemy** | 3.x | Flask ORM integration |
| **SQLAlchemy** | 2.x | DB queries, schema via models |
| **ProxyFix** (Werkzeug) | — | HTTPS/host headers from ngrok / Nginx reverse proxy |
| **Jinja2** | (bundled with Flask) | Server-side HTML templates |

**Related files:** `app.py`, `extensions.py`, `models.py`

---

#### 13.2. Database

| Technology | Role | Configuration |
|------------|------|---------------|
| **PostgreSQL** | 14+ | [Section 4](#4-set-up-postgresql-database) · schema: `schema_postgres.sql` |
| **MySQL / MariaDB** | 8+ / 10+ | [Section 5](#5-set-up-mysql--mariadb--xampp) · schema: `schema_mysql.sql` |
| **PK/FK reference** | 12 tables | [Section 6](#6-database-schema--pk--fk) |
| **psycopg2-binary** | Python ↔ PostgreSQL driver | `requirements.txt` |
| **mysql-connector-python** | Python ↔ MySQL driver | `pip install mysql-connector-python` |
| **`system_settings` table** | Runtime key-value config (API keys, OAuth, SMTP…) | Admin → Settings |
| **`users`, `documents`, `qa_results` tables** | Accounts, PDFs, generated Q&A | Created via `init_db.py` |
| **`credit_packages`, `subscription_packages`, `transactions`** | Pricing & payment history | Admin → Settings → Package management |
| **`user_auth_providers` table** | Google OAuth account linking | Auto-created on Google login |

**Related files:** `database/init_postgres.sql`, `init_db.py`, `models.py`

---

#### 13.3. User Interface (Frontend)

| Technology | Source | Role |
|------------|--------|------|
| **Bootstrap 5.3** | jsDelivr CDN | Responsive layout, UI components |
| **Bootstrap Icons** | CDN | Navbar, admin, form icons |
| **Chart.js** | `static/js/chart.umd.min.js` | Admin pie/bar charts (Bloom, algorithms, revenue) |
| **Google Fonts** | CDN | Inter, Manrope, Space Grotesk |
| **Plain HTML / CSS / JavaScript** | `templates/`, inline JS | Landing, index, PDF export, Q&A accordion |
| **Custom i18n** | `utils/translations.py` | Vietnamese/English UI — see [Section 12](#12-bilingual-ui-englishvietnamese) |

**Related files:** `templates/base.html`, `templates/admin/`, `templates/landing.html`

---

#### 13.4. Artificial Intelligence (AI / LLM)

| Technology | Role | Admin configuration |
|------------|------|---------------------|
| **OpenAI Python SDK** | Unified client for chat/completions | — |
| **OpenRouter** | LLM gateway (Gemini, Claude, GPT via one API) | API key + model → **AI model settings** |
| **Google Gemini API** | Direct calls via OpenAI-compatible endpoint | Gemini API key + model |
| **OpenAI API** | Direct GPT calls | OpenAI API key + model |
| **3-agent pipeline** | Extract PDF → generate Q&A → quality evaluation | Active AI provider/model |
| **Bloom taxonomy (6 levels)** | Classify questions Remember → Create | `utils/bloom.py`, generation form |

**Related files:** `services/pipeline.py`, `extensions.py` (`DynamicAIClient`), `config.py`

> 💡 Only **one** AI provider needs to be active; switching providers requires no code changes.

---

#### 13.5. PDF Processing & OCR

| Technology | Role | Notes |
|------------|------|-------|
| **pdfplumber** | Extract text from text-based PDFs | Default path |
| **PyMuPDF (fitz)** | Read PDFs, render page images | Pipeline support |
| **Pillow (PIL)** | Image processing for PDF pages | OCR preprocessing |
| **pytesseract** | OCR via Tesseract | Requires **Tesseract OCR** installed on the system |
| **RapidOCR (ONNX)** | OCR fallback without Tesseract | `rapidocr-onnxruntime` |
| **numpy** | Image array processing for OCR | Bundled with RapidOCR |

**Configuration:** Admin → **Enable OCR** (`enable_ocr` in `system_settings`)

**Related files:** `services/pdf.py`, `services/pipeline.py`

---

#### 13.6. Authentication, Security & Anti-spam

| Technology | Type | Role | Admin configuration |
|------------|------|------|---------------------|
| **Email/password login** | Internal | Werkzeug password hash | — |
| **Google OAuth 2.0 / OpenID Connect** | Third-party | Sign in with Google | **Integrations** → Client ID, Secret, Redirect URI |
| **Authlib** | Python library | Flask OAuth client, Google OIDC metadata | — |
| **Google reCAPTCHA v2** | Third-party | “I'm not a robot” checkbox | **Security** → Site Key + Secret Key |
| **Google reCAPTCHA v3** | Third-party | Invisible score-based (login/register) | `captcha_type` = `v3` |
| **Captcha Gate** | Internal | Extra verification page for suspected bots | Route `/captcha-gate` |
| **Flask Session + Secret Key** | Internal | Session cookies | `bootstrap.json` / Admin → Secret Key |
| **Forgot password** | Internal + SMTP | Temporary password via email | Enable in **Security** + SMTP config |

**Related files:** `app.py` (`/auth/google`, `verify_captcha`), `templates/login.html`, `templates/register.html`

---

#### 13.7. Email (SMTP)

| Technology | Role | Admin configuration |
|------------|------|---------------------|
| **smtplib** (Python stdlib) | Send email via SMTP TLS | **Security** → SMTP server settings |
| **Gmail / Outlook / custom SMTP** | Mail provider | Server, Port (587), User, App Password |

**Used for:** password recovery, pending/successful order notifications.

**Related file:** `app.py` → `send_email_smtp()`

---

#### 13.8. Payments & Credits

| Technology | Type | Role | Admin configuration |
|------------|------|------|---------------------|
| **Manual bank transfer** | Internal | Create `pending` orders, admin approval or webhook | **Payment** → bank name, account, holder |
| **VietQR (img.vietqr.io)** | Image QR API | Display transfer QR code | Bank BIN + account number |
| **SePay** | Third-party | Webhook auto-confirms transfers, adds credits | API Key + Webhook URL |
| **VNPAY** | VN payment gateway | Card/QR payment (sandbox or production) | TMN Code, Hash Secret, Return URL |
| **HMAC SHA512** | Algorithm | Sign & verify VNPAY transactions | `services/payment.py` |

**Credits flow:** `Transaction` → `status=paid` → add to `users.credits`.

**Related files:** `services/payment.py`, `app.py` (`/payment/create`, `/payment/vnpay/*`, `/payment/sepay/webhook`), `docs/vnpay_integration.md`

---

#### 13.9. Administration & System Configuration

| Component | Role |
|-----------|------|
| **Admin Panel** | Dashboard, users, transactions, stats, feedback, settings |
| **`instance/bootstrap.json`** | Initial DB URI + secret key (do not commit to Git) |
| **`system_settings` (DB)** | All runtime configuration after deployment |
| **Site Shell / Branding** | Logo, favicon, site name, SEO title/description, Open Graph |
| **`migrate_env_to_db.py`** | One-time import from legacy `.env` to DB |
| **`create_admin.py`** | CLI to create/promote admin accounts |

---

#### 13.10. Export & Experiments

| Technology | Role |
|------------|------|
| **ReportLab** | Export exam / Q&A sets to PDF |
| **NLTK** | Bloom accuracy experiments (`experiment/`) |

**Related files:** `app.py` (PDF export routes), `experiment/experiment_2_bloom_accuracy.py`

---

#### 13.11. Deployment & Development

| Technology | Role |
|------------|------|
| **Git / GitHub** | Source control |
| **ngrok** | Expose localhost over HTTPS (OAuth testing, mobile, demos) |
| **Waitress** | Production server on Windows/Linux |
| **Docker** (optional) | PostgreSQL container |

---

#### 13.12. Quick Reference — Admin Configuration Map

| Group | Admin → Settings section | Third-party service |
|-------|--------------------------|---------------------|
| AI | AI model configuration | OpenRouter, Gemini, OpenAI |
| Integrations | OAuth, VNPAY, SePay, Secret Key | Google, VNPAY, SePay |
| Payment | Bank info, VietQR BIN | VietQR API |
| Security | reCAPTCHA, SMTP, forgot password | Google reCAPTCHA, Gmail SMTP |
| Branding | Site Shell / Branding | — (local file upload) |
| Pricing | Credit packages + Subscriptions | — (stored in DB) |

> 📌 **Configuration principle:** only `bootstrap.json` is required as a local file for first startup; **all other secrets and integrations** should be configured via **Admin → Settings** (stored in the DB — PostgreSQL or MySQL), not hardcoded in source code.
