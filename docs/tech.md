### Tiếng Việt
Công nghệ sử dụng

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
### Tiếng anh
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