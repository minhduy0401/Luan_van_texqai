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
| Gộp nhiều bước trong 10 giây | Mỗi bước: nói → làm → chờ xong → chuyển bước |

**Gợi ý kỹ thuật:** VirtualBox / VMware / Hyper-V cài Windows 11, snapshot trước khi quay để quay lại nếu lỗi.

---

## Trước khi quay — Checklist (máy quay = máy người mới)

| # | Trên máy quay **chưa được có** | Ghi chú |
|---|-------------------------------|---------|
| 1 | Python, Git, XAMPP (MySQL) | Sẽ cài **trong video** |
| 2 | Folder project TEXTQAI | Sẽ **clone mới** trong video |
| 3 | `instance/bootstrap.json` | Tạo **trong video** bằng `setup_bootstrap.py` |
| 4 | Database `textqai` | Tạo **trong video** bằng `init_mysql.sql` (phpMyAdmin hoặc lệnh) |

Chỉ cần sẵn: trình duyệt, kết nối mạng, Cursor/VS Code (có thể cài nhanh 1 phút đầu).

**Text overlay cố định:** `Bước X/10`

---

## Cấu trúc video (10 bước — từ số 0)

```
⓪ Giới thiệu
① Cài Python          ② Cài Git           ③ Cài XAMPP + bật MySQL
④ Clone code (folder mới)    ⑤ venv + pip (+ driver MySQL)
⑥ Tạo DB MySQL (init_mysql.sql)   ⑦ bootstrap.json    ⑧ init_db.py
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

## PHẦN 4 — CLONE CODE VÀO FOLDER MỚI (10:00 – 13:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 10:00–10:30 | File Explorer — folder trống | *"Bước 4: tạo folder mới hoàn toàn — ví dụ D:\\TEXTQAI_Setup. Không dùng folder cũ đang dev."* | — |
| 10:30–11:30 | PowerShell cd + clone | *"Clone mã nguồn từ GitHub vào folder này."* | `cd D:\`<br>`mkdir TEXTQAI_Setup`<br>`cd TEXTQAI_Setup`<br>`git clone https://github.com/minhduy0401/Luan_van_texqai.git .` |
| 11:30–12:30 | Mở folder bằng Cursor | *"Mở thư mục bằng Cursor hoặc VS Code — viewer thấy đúng cấu trúc project."* | — |
| 12:30–13:00 | Show `database\`, `app.py` | *"Đây là mã nguồn đầy đủ. Từ đây trở đi mọi lệnh chạy trong folder này."* | — |

---

## PHẦN 5 — PYTHON VENV + PIP (13:00 – 16:30)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 13:00–13:30 | Terminal trong folder clone | *"Bước 5: tạo môi trường ảo Python trong project."* | `python -m venv venv` |
| 13:30–14:00 | Activate | *"Kích hoạt — thấy (venv) đầu dòng."* | `venv\Scripts\activate` |
| 14:00–16:00 | pip install | *"Cài thư viện — đợi 2–5 phút, có thể tua nhanh khi dựng video nhưng phải thấy lệnh chạy đủ."* | `pip install -r requirements.txt` |
| 16:00–16:30 | pip mysql driver | *"Dùng MySQL nên cài thêm driver — không có sẵn trong requirements."* | `pip install mysql-connector-python` |

---

## PHẦN 6 — TẠO DATABASE MYSQL (16:30 – 20:00)

> **Cách A — phpMyAdmin (khuyên quay):** trực quan, ít lỗi gõ lệnh. **Cách B — lệnh:** dành cho viewer quen terminal.

| Thời gian | Hình ảnh | Lời thoại | Lệnh / thao tác |
|-----------|----------|-----------|-----------------|
| 16:30–17:00 | Mở `database\init_mysql.sql` trong Cursor | *"Bước 6: file này tạo database textqai và user textqai_user. Trong repo mặc định là luanvan_ai — đổi thành textqai (Find & Replace) và sửa mật khẩu your_password nếu cần."* | — |
| 17:00–18:30 | phpMyAdmin → tab SQL | *"Mở phpMyAdmin, chọn tab SQL, copy toàn bộ nội dung init_mysql.sql, bấm Go — thấy database textqai là xong."* | `http://localhost/phpmyadmin` → SQL → Execute |
| 18:30–19:00 | Sidebar: database `textqai` | *"Kiểm tra bên trái đã có database textqai."* | — |
| 19:00–20:00 | (Tùy chọn) Lệnh XAMPP | *"Hoặc chạy lệnh — XAMPP root thường không mật khẩu, Enter khi hỏi password."* | `Get-Content database\init_mysql.sql \| & "C:\xampp\mysql\bin\mysql.exe" -u root` |

**Lưu ý trên video:** MySQL trong XAMPP phải đang **Start** (màu xanh) trước khi làm bước này.

---

## PHẦN 7 — CẤU HÌNH BOOTSTRAP (20:00 – 23:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 20:00–20:30 | Giải thích bootstrap | *"Bước 7: file instance/bootstrap.json — kết nối DB và secret key."* | — |
| 20:30–21:00 | setup_bootstrap | *"Tạo file mẫu."* | `python setup_bootstrap.py` |
| 21:00–22:30 | Sửa bootstrap.json | *"Sửa database_uri sang MySQL — dùng user textqai_user và mật khẩu đã đặt trong init_mysql.sql. XAMPP dev có thể dùng root không mật khẩu."* | `mysql+mysqlconnector://textqai_user:your_password@127.0.0.1:3306/textqai`<br>hoặc `mysql+mysqlconnector://root@127.0.0.1:3306/textqai` |
| 22:30–23:00 | URL-encode note | *"Mật khẩu có @ # % phải encode URL."* | — |

---

## PHẦN 8 — TẠO BẢNG (init_db) (23:00 – 25:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 23:00–23:30 | Giải thích | *"Bước 8: tạo 12 bảng + seed cài đặt mặc định."* | — |
| 23:30–25:00 | Chạy init_db | *"Chạy một lần — thấy OK là được."* | `python init_db.py` |

---

## PHẦN 9 — CHẠY ỨNG DỤNG (25:00 – 28:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 25:00–26:00 | venv + app.py | *"Bước 9: khởi động server."* | `python app.py` |
| 26:00–28:00 | Browser localhost:5000 | *"Mở trình duyệt — thấy landing page là thành công."* | `http://localhost:5000` |

---

## PHẦN 10 — TẠO ADMIN (28:00 – 32:00)

| Thời gian | Hình ảnh | Lời thoại | Lệnh |
|-----------|----------|-----------|------|
| 28:00–29:30 | Terminal 2 | *"Bước 10: không có admin mặc định — tạo bằng script."* | `python create_admin.py` |
| 29:30–31:00 | Login → /admin | *"Đăng nhập, vào Admin, cấu hình API key / OAuth nếu cần."* | — |
| 31:00–32:00 | Tóm tắt 10 bước | *"Xong — từ máy trắng đến website chạy được."* | — |

---

## PHẦN 11 — NGROK (TÙY CHỌN) (32:00 – 34:00)

| Hình ảnh | Lời thoại | Lệnh |
|----------|-----------|------|
| 2 terminal: app + ngrok | *"Muốn test trên điện thoại hoặc Google OAuth: mở terminal thứ hai chạy ngrok trỏ vào port 5000."* | Terminal 1: `python app.py`<br>Terminal 2: `ngrok http --domain=TEN-MIEN-CUA-BAN.ngrok-free.dev 5000` |
| Admin → Google Redirect URI | *"Vào Admin cập nhật Redirect URI cho khớp domain ngrok."* | — |
| App Flutter load URL ngrok | *"App mobile trỏ URL ngrok trong main.dart — build lại APK/iOS."* | — |

---

## PHẦN 12 — KẾT & LỖI THƯỜNG GẶP (34:00 – 38:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Slide 10 bước | *"Tóm lại: Python → Git → XAMPP → clone folder mới → venv → init_mysql → bootstrap → init_db → app.py → admin."* |
| Bảng lỗi (3–4 dòng) | *"Lỗi hay gặp — xem thêm install_guide mục 11."* |

| Lỗi trên màn hình | Cách xử lý (nói nhanh trên video) |
|-------------------|-----------------------------------|
| `python` không nhận lệnh | Chưa tick Add to PATH — cài lại Python |
| `ModuleNotFoundError` | Chưa `venv\Scripts\activate` |
| `could not connect to server` / `Can't connect to MySQL` | MySQL chưa chạy — bật Start trong XAMPP Control Panel |
| `Table 'textqai.users' doesn't exist` | Chưa chạy `python init_db.py` |
| `Access denied for user` | Sai user/mật khẩu trong `bootstrap.json` |
| `No module named 'mysql'` | Chưa `pip install mysql-connector-python` |
| `Unknown database 'textqai'` | Chưa chạy `init_mysql.sql` ở bước 6 |

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

[4] Folder mới D:\TEXTQAI_Setup → git clone ... .
[5] venv → activate → pip install -r requirements.txt
    → pip install mysql-connector-python
[6] phpMyAdmin: chạy database\init_mysql.sql (hoặc lệnh mysql XAMPP)
[7] setup_bootstrap.py → sửa bootstrap.json (URI MySQL)
[8] python init_db.py
[9] python app.py → localhost:5000
[10] python create_admin.py → /admin

[KẾT] Xong!
```

---

## Ghi chú cho người quay / dựng

1. **Mỗi bước = 1 cảnh quay liên tục** — tránh cắt giữa lệnh đang chạy.  
2. **Pause 2 giây** sau mỗi lệnh thành công để viewer chép.  
3. **Blur** mật khẩu thật trong bootstrap.json khi quay.  
4. **Phụ đề** chèn lệnh copy-paste ở cuối mỗi phần.  
5. Đính kèm mô tả video: link GitHub + link `install_guide.md`.

---

## Tham chiếu

| Tài liệu | Mục đích |
|----------|----------|
| [install_guide.md](./install_guide.md) | Hướng dẫn cài đặt đầy đủ (VI/EN) |
| [video_tutorial_script.md](./video_tutorial_script.md) | Kịch bản video **sử dụng** website |
| [user_guide.md](./user_guide.md) | Hướng dẫn người dùng cuối |
