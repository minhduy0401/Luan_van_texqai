# Kịch bản quay video — Hướng dẫn cài đặt TEXTQAI (từ đầu đến cuối)

> **Mục tiêu:** Người xem **chưa cài gì** vẫn làm theo được — quay trọn luồng từ cài Python/Git/DB → clone code → chạy website → tạo admin.  
> **Nguyên tắc quay:** **Không bỏ qua bước** vì “máy quay đã cài sẵn”. Dùng **VM Windows sạch** hoặc máy format — viewer mới hiểu.  
> **Thời lượng đề xuất:** 35–45 phút (1 video) hoặc chia **3 phần** (mục cuối).  
> **Nền tảng quay:** Windows 10/11 · Tham chiếu: [install_guide.md](./install_guide.md)

---

## Quan trọng — Quay kiểu nào người mới mới hiểu?

| ❌ Không nên | ✅ Nên làm |
|-------------|-----------|
| Máy dev đã cài Python, DB, venv sẵn — chỉ clone folder mới | **VM / máy sạch** — chưa có Python, Git, XAMPP |
| Nói “bước này các bạn tự cài” rồi cắt cảnh | **Quay luôn** màn hình tải + Next + Finish installer |
| Nhảy thẳng vào `bootstrap.json` | Clone vào **folder mới trống** (vd. `D:\TEXTQAI_Setup`) |
| Gõ `database_uri` vào PowerShell | URI **chỉ ghi trong file** `instance/bootstrap.json` |
| `pip install` ở folder cha (không thấy requirements.txt) | Terminal phải nằm **cùng folder với `app.py`** |
| Gộp nhiều bước trong 10 giây | Mỗi bước: nói → làm → chờ xong → chuyển bước |

**Gợi ý kỹ thuật:** VirtualBox / VMware / Hyper-V cài Windows 11, snapshot trước khi quay để quay lại nếu lỗi.

---

## Trước khi quay — Checklist (máy quay = máy người mới)

| # | Trên máy quay **chưa được có** | Ghi chú |
|---|-------------------------------|---------|
| 1 | Python, Git, XAMPP (MySQL) | Sẽ cài **trong video** |
| 2 | Folder project TEXTQAI | Sẽ **clone mới** trong video |
| 3 | `instance/bootstrap.json` | Tạo **trong video** bằng `setup_bootstrap.py` |
| 4 | Database `textqai` | Tạo **trong video** bằng SQL ngắn trong phpMyAdmin |

Chỉ cần sẵn: trình duyệt, kết nối mạng, Cursor/VS Code (có thể cài nhanh 1 phút đầu).

**Text overlay cố định:** `Bước X/10`

---

## Cấu trúc video (10 bước — từ số 0)

```
⓪ Giới thiệu
① Cài Python          ② Cài Git           ③ Cài XAMPP + bật MySQL
④ Clone code (folder mới)    ⑤ venv + pip (+ driver MySQL)
⑥ Tạo DB `textqai` (phpMyAdmin)   ⑦ bootstrap.json (sửa file, không gõ terminal)   ⑧ init_db.py
⑨ python app.py       ⑩ create_admin + mở trình duyệt
```

---

## PHẦN 0 — MỞ ĐẦU (0:00 – 1:30)

| Thời gian | Hình ảnh | Lời thoại |
|-----------|----------|-----------|
| 0:00–0:30 | Logo + desktop Windows sạch | *"Video này cài TEXTQAI từ con số 0 — giả sử máy bạn chưa có Python, chưa có database, chưa có code. Làm y chang từng bước là chạy được."* |
| 0:30–1:00 | Slide checklist 10 bước | *"Chúng ta sẽ: cài Python, Git, XAMPP (MySQL), clone code vào folder mới, cấu hình, chạy web và tạo tài khoản admin."* |
| 1:00–1:30 | — | *"Bước 1: cài Python."* |

---

## PHẦN 1 — CÀI PYTHON (1:30 – 4:00)

| Thời gian | Hình ảnh | Lời thoại |
|-----------|----------|-----------|
| 1:30–2:30 | python.org → Download 3.12 | *"Vào python.org, tải bản 3.10 trở lên cho Windows."* |
| 2:30–3:30 | Installer — tick **Add python.exe to PATH** | *"Quan trọng: tick Add to PATH ở màn đầu, rồi Install Now. Nếu quên bước này, lệnh python sẽ không chạy."* |
| 3:30–4:00 | PowerShell mới: `python --version` | *"Mở PowerShell mới, gõ python --version — thấy 3.10+ là xong bước 1."* | `python --version` |

---

## PHẦN 2 — CÀI GIT (4:00 – 6:00)

| Thời gian | Hình ảnh | Lời thoại |
|-----------|----------|-----------|
| 4:00–5:00 | git-scm.com → download | *"Bước 2: cài Git — tải installer Windows, Next liên tục, giữ mặc định."* |
| 5:00–6:00 | `git --version` | *"Kiểm tra: git --version."* | `git --version` |

---

## PHẦN 3 — CÀI XAMPP + BẬT MYSQL (6:00 – 10:00)

> XAMPP phổ biến trên Windows — có sẵn MySQL + phpMyAdmin, không cần cấu hình phức tạp như PostgreSQL.

| Thời gian | Hình ảnh | Lời thoại |
|-----------|----------|-----------|
| 6:00–8:00 | apachefriends.org → tải XAMPP Windows | *"Bước 3: cài XAMPP — tải bản Windows, Next liên tục, cài vào C:\\xampp mặc định."* |
| 8:00–8:45 | XAMPP Control Panel → Start **MySQL** | *"Mở XAMPP Control Panel, bấm Start ở dòng MySQL — chuyển sang màu xanh là MySQL đang chạy. Apache không bắt buộc cho TEXTQAI."* |
| 8:45–9:30 | Mở `http://localhost/phpmyadmin` | *"Mở phpMyAdmin trên trình duyệt — đăng nhập user root, XAMPP mặc định thường không cần mật khẩu."* |
| 9:30–10:00 | — | *"Phần tạo database textqai sẽ làm ở bước 6 — sau khi đã clone code, vì script nằm trong repo."* |

**Note (15 giây):** *"Muốn dùng PostgreSQL thay MySQL — xem install_guide mục 4; video này dùng MySQL vì dễ hơn cho người mới."*

---

## PHẦN 4 — CLONE CODE VÀO FOLDER MỚI (10:00 – 14:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 10:00–10:30 | File Explorer — folder trống | *"Bước 4: tạo folder mới — ví dụ D:\\TEXTQAI_Setup."* | — |
| 10:30–11:30 | PowerShell cd + clone | *"Clone từ GitHub. **Quan trọng:** dấu chấm `.` ở cuối — code nằm thẳng trong folder này, không tạo folder con."* | `cd D:\`<br>`mkdir TEXTQAI_Setup`<br>`cd TEXTQAI_Setup`<br>`git clone https://github.com/minhduy0401/Luan_van_texqai.git .` |
| 11:30–12:00 | `dir` — thấy `app.py`, `requirements.txt` | *"Kiểm tra: phải thấy app.py và requirements.txt ngay tại đây. Nếu chỉ thấy folder Luan_van_texqai bên trong — nghĩa là quên dấu chấm, cd vào folder con đó."* | `dir app.py`<br>`dir requirements.txt` |
| 12:00–13:00 | Mở folder bằng Cursor/VS Code | *"Open Folder → chọn đúng thư mục có app.py — terminal trong IDE sẽ đúng chỗ."* | — |
| 13:00–14:00 | Show `database\`, `instance\` | *"Từ bước 5 trở đi, mọi lệnh chạy trong folder có app.py."* | — |

> **Nếu đã clone không có dấu `.`:** `cd D:\TEXTQAI_Setup\Luan_van_texqai` — làm tiếp từ folder đó.

---

## PHẦN 5 — PYTHON VENV + PIP (14:00 – 17:30)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 14:00–14:15 | Terminal — pwd / prompt | *"Bước 5: xác nhận đang ở folder project — prompt phải là …\\TEXTQAI_Setup hoặc …\\Luan_van_texqai (có app.py)."* | `dir requirements.txt` |
| 14:15–14:45 | Tạo venv | *"Tạo môi trường ảo **trong folder project**, không tạo ở folder cha."* | `python -m venv venv` |
| 14:45–15:15 | Activate | *"Kích hoạt — thấy (venv) đầu dòng."* | `venv\Scripts\activate` |
| 15:15–17:00 | pip install | *"Cài thư viện — có thể tua nhanh khi dựng nhưng phải thấy lệnh chạy đủ."* | `pip install -r requirements.txt` |
| 17:00–17:30 | Driver MySQL | *"MySQL cần driver riêng — không có trong requirements.txt."* | `pip install mysql-connector-python` |

---

## PHẦN 6 — TẠO DATABASE MYSQL (17:30 – 21:00)

> **Khuyên quay:** chỉ tạo database bằng SQL ngắn trong phpMyAdmin — **không** chạy `CREATE USER` trên XAMPP (hay lỗi `#1034 global_priv corrupt`).

| Thời gian | Hình ảnh | Lời thoại | Lệnh / thao tác |
|-----------|----------|-----------|-----------------|
| 17:30–18:00 | XAMPP — MySQL Start (xanh) | *"Bước 6: MySQL phải đang chạy."* | — |
| 18:00–19:30 | phpMyAdmin → tab SQL | *"Mở phpMyAdmin, tab SQL, dán và chạy **chỉ** lệnh tạo database — XAMPP dev dùng user root, không cần tạo user riêng."* | Xem khối SQL bên dưới |
| 19:30–20:00 | Sidebar: database `textqai` | *"Kiểm tra bên trái đã có database textqai."* | — |
| 20:00–21:00 | (Tùy chọn) File init_mysql.sql | *"File init_mysql.sql trong repo mặc định tên luanvan_ai — nếu dùng file đó, Find & Replace thành textqai. Hoặc bỏ qua CREATE USER nếu XAMPP báo lỗi quyền."* | — |

**SQL chạy trong phpMyAdmin (copy-paste, khuyên dùng):**

```sql
CREATE DATABASE IF NOT EXISTS textqai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

**Lưu ý trên video:** MySQL XAMPP phải **Start** trước. Lỗi `global_priv corrupt` → bỏ qua CREATE USER, chỉ chạy khối SQL trên.

---

## PHẦN 7 — CẤU HÌNH BOOTSTRAP (21:00 – 25:00)

> **Quan trọng:** `database_uri` là **nội dung file JSON**, không gõ vào PowerShell.

| Thời gian | Hình ảnh | Lời thoại | Lệnh / nội dung |
|-----------|----------|-----------|-----------------|
| 21:00–21:30 | Giải thích bootstrap | *"Bước 7: file instance/bootstrap.json — app đọc kết nối DB từ đây."* | — |
| 21:30–22:00 | Terminal | *"Tạo file mẫu."* | `python setup_bootstrap.py` |
| 22:00–23:30 | **Mở và sửa** `instance/bootstrap.json` trong editor | *"Mở file trong VS Code — sửa hai trường. database_uri: chuỗi kết nối MySQL. secret_key: chuỗi bí mật tự đặt cho Flask session — dev có thể dùng chuỗi dài bất kỳ, không phải API key."* | Xem JSON mẫu bên dưới |
| 23:30–24:30 | Zoom JSON — **không** gõ URI vào terminal | *"Lưu file Ctrl+S. **Không** paste mysql+mysqlconnector://… vào PowerShell — đó không phải lệnh."* | — |
| 24:30–25:00 | URL-encode note | *"Mật khẩu MySQL có @ # % phải encode URL trong URI."* | — |

**Nội dung mẫu `instance/bootstrap.json` (XAMPP, root không mật khẩu):**

```json
{
  "database_uri": "mysql+mysqlconnector://root@127.0.0.1:3306/textqai",
  "secret_key": "a8fK2mP9xQ7vL4nR1wT6yU3zB0cD5eG8"
}
```

| Trường | Ý nghĩa |
|--------|---------|
| `database_uri` | Kết nối MySQL — tên DB phải khớp bước 6 (`textqai`) |
| `secret_key` | Bí mật Flask (session đăng nhập) — tự đặt, giữ cố định trên máy |

---

## PHẦN 8 — TẠO BẢNG (init_db) (25:00 – 27:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 25:00–25:30 | Giải thích | *"Bước 8: sau khi bootstrap.json đã lưu — script Python tạo 12 bảng + seed cài đặt mặc định."* | — |
| 25:30–27:00 | Terminal — venv active | *"Chạy một lần — thấy danh sách bảng có dấu ✓ là thành công."* | `python init_db.py` |

---

## PHẦN 9 — CHẠY ỨNG DỤNG (27:00 – 30:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 27:00–28:00 | venv + app.py | *"Bước 9: khởi động server."* | `python app.py` |
| 28:00–30:00 | Browser localhost:5000 | *"Mở trình duyệt — thấy landing page là thành công."* | `http://localhost:5000` |

---

## PHẦN 10 — TẠO ADMIN (30:00 – 34:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 30:00–31:30 | Terminal 2 — cùng folder project | *"Bước 10: không có admin mặc định — tạo bằng script."* | `python create_admin.py` |
| 31:30–33:00 | Login → /admin | *"Đăng nhập, vào Admin, cấu hình API key / OAuth nếu cần."* | — |
| 33:00–34:00 | Tóm tắt 10 bước | *"Xong — từ máy trắng đến website chạy được."* | — |

---

## PHẦN 11 — NGROK (TÙY CHỌN) (34:00 – 36:00)

| Hình ảnh | Lời thoại | Lệnh |
|----------|-----------|------|
| 2 terminal: app + ngrok | *"Muốn test trên điện thoại hoặc Google OAuth: mở terminal thứ hai chạy ngrok trỏ vào port 5000."* | Terminal 1: `python app.py`<br>Terminal 2: `ngrok http --domain=TEN-MIEN-CUA-BAN.ngrok-free.dev 5000` |
| Admin → Google Redirect URI | *"Vào Admin cập nhật Redirect URI cho khớp domain ngrok."* | — |
| App Flutter load URL ngrok | *"App mobile trỏ URL ngrok trong main.dart — build lại APK/iOS."* | — |

---

## PHẦN 12 — KẾT & LỖI THƯỜNG GẶP (36:00 – 40:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Slide 10 bước | *"Tóm lại: Python → Git → XAMPP → clone folder mới → venv → init_mysql → bootstrap → init_db → app.py → admin."* |
| Bảng lỗi (3–4 dòng) | *"Lỗi hay gặp — xem thêm install_guide mục 11."* |

| Lỗi trên màn hình | Cách xử lý (nói nhanh trên video) |
|-------------------|-----------------------------------|
| `No such file or directory: requirements.txt` | Sai folder — `cd` vào chỗ có `app.py`, hoặc clone thiếu dấu `.` → vào `Luan_van_texqai` |
| `The term 'mysql+mysqlconnector://…' is not recognized` | Gõ URI vào PowerShell — phải ghi vào `instance/bootstrap.json` |
| `#1034 global_priv corrupt` (CREATE USER) | XAMPP lỗi bảng hệ thống — chỉ chạy `CREATE DATABASE textqai`, dùng `root` trong bootstrap |
| `python` không nhận lệnh | Chưa tick Add to PATH — cài lại Python |
| `ModuleNotFoundError` | Chưa `venv\Scripts\activate` |
| `Can't connect to MySQL` | MySQL chưa Start trong XAMPP Control Panel |
| `Table 'textqai.users' doesn't exist` | Chưa chạy `python init_db.py` hoặc chưa lưu bootstrap.json |
| `No module named 'mysql'` | Chưa `pip install mysql-connector-python` |
| `Unknown database 'textqai'` | Chưa tạo DB ở bước 6 — hoặc tên DB không khớp URI |

---

## Gợi ý chia 3 video

| Video | Nội dung | Thời lượng |
|-------|----------|------------|
| **Tập 1** | Cài Python + Git + XAMPP (MySQL) | ~10 phút |
| **Tập 2** | Clone → venv → DB → bootstrap → init_db | ~15 phút |
| **Tập 3** | Chạy app → admin → ngrok → lỗi thường gặp | ~12 phút |

---

## Teleprompter — từ đầu đến cuối

```
[MỞ] Máy trắng — cài TEXTQAI từ số 0.

[1] Cài Python (tick Add to PATH) → python --version
[2] Cài Git → git --version
[3] Cài XAMPP → Start MySQL → mở phpMyAdmin

[4] D:\TEXTQAI_Setup
    git clone https://github.com/minhduy0401/Luan_van_texqai.git .
    dir app.py          ← phải thấy file
    Open Folder trong VS Code (folder có app.py)

[5] python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    pip install mysql-connector-python

[6] phpMyAdmin → SQL → chỉ CREATE DATABASE textqai
    (không CREATE USER trên XAMPP)

[7] python setup_bootstrap.py
    Sửa instance/bootstrap.json (KHÔNG gõ URI vào terminal):
    {
      "database_uri": "mysql+mysqlconnector://root@127.0.0.1:3306/textqai",
      "secret_key": "chuoi-bi-mat-tu-dat"
    }
    Ctrl+S lưu file

[8] python init_db.py   ← tạo 12 bảng
[9] python app.py → http://localhost:5000
[10] python create_admin.py → /admin

[KẾT] Xong!
```

---

## Ghi chú cho người quay / dựng

1. **Mỗi bước = 1 cảnh quay liên tục** — tránh cắt giữa lệnh đang chạy.  
2. **Pause 2 giây** sau mỗi lệnh thành công để viewer chép.  
3. **Quay rõ:** `dir app.py` sau clone; mở `bootstrap.json` trong editor (không paste URI vào terminal).  
4. **Blur** mật khẩu / secret_key thật khi publish.  
5. **Phụ đề** chèn lệnh copy-paste ở cuối mỗi phần.  
6. Đính kèm mô tả video: link GitHub + link `install_guide.md`.

---

## Tham chiếu

| Tài liệu | Mục đích |
|----------|----------|
| [install_guide.md](./install_guide.md) | Hướng dẫn cài đặt đầy đủ (VI/EN) |
| [video_tutorial_script.md](./video_tutorial_script.md) | Kịch bản video **sử dụng** website |
| [user_guide.md](./user_guide.md) | Hướng dẫn người dùng cuối |
