# TEXTQAI

**TEXTQAI** là hệ thống web tự động sinh **câu hỏi – đáp án** từ giáo trình PDF theo **Thang phân loại Bloom** (6 cấp độ nhận thức). Dự án phục vụ giáo dục, hỗ trợ giảng viên và sinh viên tạo ngân hàng câu hỏi bám sát nội dung tài liệu gốc.

---

## Tính năng chính

- Upload PDF giáo trình hoặc chọn tài liệu có sẵn trong hệ thống
- Sinh câu hỏi theo từng mức **Bloom 1 → Bloom 6** (Nhớ → Sáng tạo)
- Pipeline **3 tác nhân AI**: trích xuất nội dung → sinh Q&A → đánh giá chất lượng
- Hỗ trợ PDF text và PDF scan (OCR)
- Xuất đề kiểm tra ra **PDF**
- Quản lý tài khoản, **credits**, thanh toán (SePay / VNPAY)
- Đăng nhập Google OAuth
- Giao diện song ngữ **Việt / Anh**

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| Backend | Python 3.10+, Flask |
| Database | PostgreSQL 14+ |
| AI | OpenRouter / Gemini / OpenAI (qua OpenAI SDK) |
| PDF | pdfplumber, PyMuPDF, RapidOCR, pytesseract |
| Frontend | Jinja2 templates, HTML/CSS/JS |

---

## Yêu cầu hệ thống

- Python **3.10+**
- Git **2.30+**
- PostgreSQL **14+** (cài riêng — không cần XAMPP)
- RAM **2 GB** trở lên
- API key từ [OpenRouter](https://openrouter.ai) hoặc [Google AI Studio](https://aistudio.google.com)

---

## Cài đặt nhanh

```bash
git clone https://github.com/minhduy0401/Luan_van_texqai.git
cd Luan_van_texqai

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Cấu hình

#### 1. Cài PostgreSQL

**Windows** — tải installer tại [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) hoặc:

```powershell
winget install PostgreSQL.PostgreSQL.17
```

Ghi nhớ mật khẩu user `postgres` khi cài.

**Docker** (tùy chọn):

```bash
docker run -d --name textqai-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

Tạo database và user:

```bash
psql -U postgres -f database/init_postgres.sql
psql -U postgres -d luanvan_ai -c "GRANT ALL ON SCHEMA public TO textqai_user;"
psql -U postgres -d luanvan_ai -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO textqai_user;"
```

> Dev nhanh: có thể dùng luôn user `postgres` trong URI (không cần `textqai_user`).

#### 2. Bootstrap kết nối PostgreSQL (`instance/bootstrap.json`)

Chỉ **một file bootstrap** (không dùng `.env`) — để app biết cách kết nối DB lần đầu:

```bash
python setup_bootstrap.py
```

Sửa `instance/bootstrap.json`:

```json
{
  "database_uri": "postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/luanvan_ai",
  "secret_key": "your-secret-key-until-admin-updates"
}
```

> Mật khẩu có ký tự đặc biệt (`@`, `#`…) phải [URL-encode](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls) trong URI.

> Mọi cấu hình khác (API key, OAuth, VNPAY, OCR, model AI…) lưu trong **Admin → Cài đặt hệ thống** (`system_settings`).

**Chuyển từ `.env` cũ:** `python migrate_env_to_db.py` (một lần), rồi cấu hình qua Admin.

> URI dùng **`postgresql+psycopg2`**. MySQL/XAMPP legacy: `database/init_mysql.sql` + `mysql+mysqlconnector://...`

#### 3. Tạo bảng (schema)

```bash
python init_db.py
```

Script này gọi `db.create_all()` và tạo 12 bảng từ `models.py`:

| Bảng | Mô tả |
|------|--------|
| `users`, `user_auth_providers` | Tài khoản, đăng nhập local/Google |
| `documents`, `qa_results` | PDF và câu hỏi đã sinh |
| `agent1/2/3_evaluation_logs` | Log pipeline AI |
| `credit_packages`, `subscription_packages`, `transactions` | Thanh toán |
| `feedbacks`, `system_settings` | Phản hồi, cấu hình admin |

> Lần chạy `python app.py` cũng tự gọi `db.create_all()` nếu chưa có bảng — `init_db.py` giúp kiểm tra riêng trước khi khởi động web.

#### 4. Khởi động ứng dụng

```bash
python app.py
```

Truy cập: **http://localhost:5000**

#### 5. Tạo tài khoản admin

Hệ thống **không** có sẵn admin mặc định. Sau khi app chạy được, tạo admin bằng script:

```bash
python create_admin.py
```

Script sẽ hỏi username, email (tùy chọn), mật khẩu và tạo user với `is_admin=True`.

**Cách khác** — đăng ký qua `/register` rồi nâng quyền:

```bash
python create_admin.py --username ten_ban_vua_dang_ky --promote
```

Hoặc trực tiếp trong PostgreSQL (sau khi đã đăng ký):

```sql
UPDATE users SET is_admin = TRUE WHERE username = 'ten_tai_khoan';
```

> Chi tiết: [docs/install_guide.md](docs/install_guide.md)

---

## Cấu trúc dự án

```
Luan_van_texqai/
├── app.py              # Flask entry point, routes
├── config.py           # Model AI, hằng số
├── extensions.py       # DB, Login, OAuth, AI client
├── models.py           # SQLAlchemy models
├── init_db.py          # Tạo bảng PostgreSQL lần đầu
├── setup_bootstrap.py  # Tạo instance/bootstrap.json
├── migrate_env_to_db.py # Import .env cũ → system_settings
├── create_admin.py     # Tạo / nâng quyền tài khoản admin
├── migrate_db.py       # Migration một lần (schema cũ → mới)
├── database/
│   ├── init_postgres.sql  # Script CREATE DATABASE (PostgreSQL)
│   └── init_mysql.sql     # Legacy XAMPP/MySQL
├── requirements.txt
├── services/
│   ├── pipeline.py     # Pipeline 3 agent (A1 → A2 → A3)
│   ├── pdf.py          # Trích xuất & OCR PDF
│   └── payment.py      # SePay, VNPAY
├── templates/          # Giao diện web
├── static/             # Logo, favicon
├── utils/              # Bloom, helpers, i18n
├── docs/               # Tài liệu hướng dẫn
└── experiment/         # Script thực nghiệm BLEU & Bloom accuracy
```

---

## Tài liệu

| Tài liệu | Mô tả |
|----------|--------|
| [docs/install_guide.md](docs/install_guide.md) | Hướng dẫn cài đặt (VI / EN) |
| [docs/user_guide.md](docs/user_guide.md) | Hướng dẫn sử dụng (VI / EN) |
| [docs/vnpay_integration.md](docs/vnpay_integration.md) | Tích hợp VNPAY |

---

## Pipeline AI

```mermaid
flowchart LR
    PDF[PDF giáo trình] --> A1[Agent 1\nKhả thi Bloom]
    A1 --> A2[Agent 2\nSinh Q&A]
    A2 --> A3[Agent 3\nĐánh giá chất lượng]
    A3 -->|pass| OUT[Câu hỏi + Đáp án]
    A3 -->|fail| A2
```

| Agent | Vai trò |
|-------|---------|
| **Agent 1** | Kiểm tra section có đủ nội dung cho mức Bloom yêu cầu |
| **Agent 2** | Sinh câu hỏi và đáp án bám nguồn tài liệu |
| **Agent 3** | Chấm điểm groundedness, Bloom verb, đa dạng ý — fail thì A2 thử lại |

---

## Thang Bloom

| Cấp | Tên | Loại câu hỏi |
|-----|-----|--------------|
| B1 | Nhớ | Liệt kê, định nghĩa |
| B2 | Hiểu | Giải thích, mô tả |
| B3 | Vận dụng | Áp dụng vào tình huống |
| B4 | Phân tích | So sánh, phân loại |
| B5 | Đánh giá | Nhận xét, biện luận |
| B6 | Sáng tạo | Đề xuất, thiết kế |


---

## Liên hệ

Repository: [github.com/minhduy0401/Luan_van_texqai](https://github.com/minhduy0401/Luan_van_texqai)
