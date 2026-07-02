# TEXTQAI

**TEXTQAI** là hệ thống web tự động sinh **câu hỏi – đáp án** từ giáo trình PDF theo **Thang phân loại Bloom** (6 cấp độ nhận thức). Hệ thống hỗ trợ giảng viên xây dựng ngân hàng câu hỏi bám sát nội dung tài liệu gốc, có thể gắn thêm **Chuẩn đầu ra (CLO)** cho từng mức Bloom.

**Demo:** [textqai.azurewebsites.net](https://textqai.azurewebsites.net)

**Repository:** [github.com/minhduy0401/Luan_van_texqai](https://github.com/minhduy0401/Luan_van_texqai)

---

## Tính năng chính

- Upload PDF giáo trình hoặc chọn tài liệu có sẵn trong hệ thống
- Sinh câu hỏi theo từng mức **Bloom 1 → Bloom 6** (Nhớ → Sáng tạo)
- **Chuẩn đầu ra (CLO)** tùy chọn cho mỗi dòng Bloom — hướng pipeline chọn mục và kiểm tra Q&A bám CLO
- Pipeline **3 tác nhân AI**: kiểm tra khả thi → sinh Q&A → đánh giá chất lượng
- Hỗ trợ PDF text và PDF scan (OCR)
- Xuất đề kiểm tra ra **PDF** (CLO ẩn trên đề thi, hiển thị ở đáp án)
- Quản lý tài khoản, **credits**, thanh toán (SePay / VNPAY)
- Đăng nhập Google OAuth
- Giao diện song ngữ **Việt / Anh**

---

## Chuẩn đầu ra (CLO)

Mỗi dòng cấu hình Bloom có thể nhập **Chuẩn đầu ra** (tối đa 2000 ký tự). Trường này **tùy chọn** — để trống thì hệ thống hoạt động như trước.

| Giai đoạn | Vai trò CLO |
|-----------|-------------|
| **Chọn mục nguồn** | Xếp hạng section theo độ trùng CLO (tiêu đề + nội dung mục) |
| **Agent 1** | Lọc mục có chủ đề/năng lực phù hợp CLO (Bloom ceiling vẫn strict) |
| **Agent 2** | Sinh Q&A bám CLO và mục nguồn |
| **Agent 3** | Kiểm tra heuristic + LLM: Q&A có đánh giá đúng CLO không |
| **Lưu trữ / PDF** | Lưu `learning_outcome` trong DB; hiển thị ở lịch sử và PDF đáp án |

**Lưu ý thực tế:** Một CLO học phần thường mô tả nhiều năng lực (vd. khái niệm + mô hình + thuật ngữ). Với **Bloom 1–2**, mỗi câu hỏi chỉ cần bám **một khía cạnh** phù hợp mục nguồn — không gộp hết CLO vào một câu.

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| Backend | Python 3.10+, Flask |
| Database | PostgreSQL 14+ |
| AI | OpenRouter / Gemini / OpenAI (OpenAI SDK) |
| PDF | pdfplumber, PyMuPDF, RapidOCR, pytesseract, ReportLab |
| Frontend | Jinja2 templates, HTML/CSS/JS |

---

## Yêu cầu hệ thống

- Python **3.10+**
- Git **2.30+**
- PostgreSQL **14+**
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

### 1. Cài PostgreSQL

**Windows** — [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) hoặc:

```powershell
winget install PostgreSQL.PostgreSQL.17
```

**Docker** (tùy chọn):

```bash
docker run -d --name textqai-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

Tạo database:

```bash
psql -U postgres -f database/init_postgres.sql
psql -U postgres -d luanvan_ai -c "GRANT ALL ON SCHEMA public TO textqai_user;"
psql -U postgres -d luanvan_ai -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO textqai_user;"
```

### 2. Bootstrap DB (`instance/bootstrap.json`)

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

> Mật khẩu có ký tự đặc biệt phải [URL-encode](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls) trong URI.

> API key, OAuth, VNPAY, OCR, model AI… cấu hình trong **Admin → Cài đặt hệ thống** (`system_settings`).

**Chuyển từ `.env` cũ:** `python migrate_env_to_db.py` (một lần).

### 3. Tạo bảng

```bash
python init_db.py
```

| Bảng | Mô tả |
|------|--------|
| `users`, `user_auth_providers` | Tài khoản, đăng nhập local/Google |
| `documents`, `qa_results` | PDF và câu hỏi (có cột `learning_outcome`) |
| `agent1/2/3_evaluation_logs` | Log pipeline AI |
| `credit_packages`, `subscription_packages`, `transactions` | Thanh toán |
| `feedbacks`, `system_settings` | Phản hồi, cấu hình admin |

> `python app.py` tự gọi `db.create_all()` và bổ sung cột mới (vd. `learning_outcome`) khi khởi động.

### 4. Chạy ứng dụng

```bash
python app.py
```

Truy cập: **http://localhost:5000**

### 5. Tạo admin

```bash
python create_admin.py
```

Hoặc đăng ký qua `/register` rồi:

```bash
python create_admin.py --username ten_tai_khoan --promote
```

> Hướng dẫn chi tiết: [docs/install_guide.md](docs/install_guide.md)

---

## Cấu trúc dự án

```
Luan_van_texqai/
├── app.py                 # Flask routes, PDF export, xử lý form CLO
├── config.py              # Model AI, hằng số
├── extensions.py          # DB, Login, OAuth, AI client
├── models.py              # SQLAlchemy models (QAResult.learning_outcome)
├── init_db.py             # Tạo bảng PostgreSQL
├── setup_bootstrap.py     # Tạo instance/bootstrap.json
├── migrate_env_to_db.py   # Import .env cũ → system_settings
├── create_admin.py        # Tạo / nâng quyền admin
├── database/
│   ├── init_postgres.sql
│   └── init_mysql.sql     # Legacy MySQL
├── services/
│   ├── pipeline.py        # Pipeline 3 agent + CLO ranking/validation
│   ├── pdf.py             # Trích xuất & OCR PDF
│   └── payment.py         # SePay, VNPAY
├── templates/             # Giao diện web (textarea CLO trên index)
├── static/
│   └── fonts/             # DejaVu Sans — PDF tiếng Việt
├── utils/                 # Bloom, helpers, i18n
├── docs/                  # Tài liệu hướng dẫn
└── experiment/            # BLEU & Bloom accuracy
```

---

## Pipeline AI

```mermaid
flowchart LR
    PDF[PDF giáo trình] --> CLO{Có CLO?}
    CLO -->|Có| Rank[Xếp hạng mục theo CLO]
    CLO -->|Không| A1
    Rank --> A1[Agent 1\nBloom + CLO]
    A1 --> A2[Agent 2\nSinh Q&A]
    A2 --> A3[Agent 3\nChấm chất lượng]
    A3 -->|pass| OUT[Câu hỏi + Đáp án]
    A3 -->|fail| A2
```

| Agent | Vai trò |
|-------|---------|
| **Agent 1** | Kiểm tra section đủ nội dung cho mức Bloom; lọc CLO nếu có |
| **Agent 2** | Sinh câu hỏi và đáp án bám mục nguồn + CLO (nếu có) |
| **Agent 3** | Groundedness, Bloom verb, đa dạng ý, kiểm CLO — fail thì A2 thử lại (tối đa 5 lần) |

---

## Thang Bloom

| Cấp | Tên | Loại câu hỏi |
|-----|-----|--------------|
| B1 | Nhớ | Liệt kê, định nghĩa |
| B2 | Hiểu | Giải thích, mô tả |
| B3 | Vận dụng | Áp dụng vào tình huống |
| B4 | Phân tích | So sánh, phân loại, mối quan hệ |
| B5 | Đánh giá | Nhận xét, biện luận |
| B6 | Sáng tạo | Đề xuất, thiết kế |

---

## Tài liệu

| Tài liệu | Mô tả |
|----------|--------|
| [docs/install_guide.md](docs/install_guide.md) | Hướng dẫn cài đặt (VI / EN) |
| [docs/user_guide.md](docs/user_guide.md) | Hướng dẫn sử dụng (VI / EN) |
| [docs/tech.md](docs/tech.md) | Kiến trúc kỹ thuật, i18n, tích hợp |
| [docs/vnpay_integration.md](docs/vnpay_integration.md) | Tích hợp VNPAY |

---

## Triển khai (Azure App Service)

1. Push code lên GitHub
2. Azure App Service kết nối repo, branch `main`
3. Cấu hình `instance/bootstrap.json` hoặc biến môi trường tương đương trên server
4. PostgreSQL (Azure Database for PostgreSQL hoặc instance riêng)
5. Chạy migration DB một lần nếu nâng cấp từ bản cũ (cột `learning_outcome` tự thêm khi app khởi động)

---

## Liên hệ

Repository: [github.com/minhduy0401/Luan_van_texqai](https://github.com/minhduy0401/Luan_van_texqai)
