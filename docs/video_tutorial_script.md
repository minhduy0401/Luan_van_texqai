# Kịch bản quay video hướng dẫn sử dụng TEXTQAI (Website)

> **Mục tiêu video:** Người xem mới (giảng viên, trợ giảng) xem xong có thể tự đăng ký → upload giáo trình → sinh câu hỏi Bloom → xuất đề PDF.  
> **Thời lượng đề xuất:** 18–25 phút (bản đầy đủ) hoặc cắt thành 4 clip ngắn (mục cuối).  
> **Ngôn ngữ thuyết minh:** Tiếng Việt (có thể ghi phụ đề EN sau).  
> **Cập nhật:** 06/2026

---

## Chuẩn bị trước khi quay

| Hạng mục | Ghi chú |
|----------|---------|
| Tài khoản demo | Có ≥ 15 credits |
| File PDF mẫu | Có text chọn được (10–30 trang), không phải scan |
| Trình duyệt | Chrome, 1920×1080, zoom 100%, ẩn bookmark bar |
| Môi trường | Tắt thông báo hệ thống, mic riêng, giảm tiếng ồn |
| Ghi hình | OBS / Camtasia, con trỏ to, click chậm rõ ràng |

---

## PHẦN 0 — MỞ ĐẦU (0:00 – 1:30)

| Thời gian | Hình ảnh trên màn hình | Lời thoại (thuyết minh) | Chú thích kỹ thuật |
|-----------|------------------------|-------------------------|-------------------|
| 0:00–0:15 | Logo TEXTQAI + tiêu đề intro | *"Xin chào! Video này hướng dẫn chi tiết cách sử dụng website TEXTQAI — nền tảng sinh câu hỏi và đáp án tự luận từ giáo trình PDF theo thang Bloom."* | Intro 5–10 giây, nhạc nền nhẹ |
| 0:15–0:45 | Landing page (`/?landing=1`) — scroll chậm qua hero, tính năng, workflow | *"TEXTQAI giúp bạn: tải giáo trình PDF, cấu hình số câu theo 6 mức Bloom, sinh câu hỏi bằng AI, lưu lịch sử và xuất đề kiểm tra PDF có hoặc không có đáp án — tất cả trên trình duyệt, không cần cài phần mềm."* | Zoom nhẹ vào tagline và 3 metric cards |
| 0:45–1:15 | Bảng Bloom 1–6 (trong landing hoặc user guide) | *"Hệ thống dùng pipeline 3 tác nhân AI: trích xuất nội dung → sinh câu hỏi theo Bloom → đánh giá chất lượng. Mỗi câu sinh ra tiêu tốn 1 credit."* | Text overlay: Bloom 1 Nhớ → Bloom 6 Sáng tạo |
| 1:15–1:30 | — | *"Bắt đầu từ bước đăng ký tài khoản."* | Chuyển cảnh mượt |

**Text overlay góc trái:** `PHẦN 1 — ĐĂNG KÝ & ĐĂNG NHẬP`

---

## PHẦN 1 — ĐĂNG KÝ & ĐĂNG NHẬP (1:30 – 5:00)

### 1.1 Chuyển ngôn ngữ (1:30 – 2:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Landing → góc phải dropdown **🌐 Tiếng Việt / English** (web) hoặc nút **VI \| EN** (app) | *"Website hỗ trợ song ngữ Việt–Anh. Chọn ngôn ngữ ở góc trên — toàn bộ giao diện workspace sẽ đổi theo. Trang đăng ký và đăng nhập tự theo ngôn ngữ bạn đã chọn trên trang chủ."* |

### 1.2 Đăng ký bằng Email (2:00 – 3:15)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Nhấn **Đăng ký** trên landing → `/register` | *"Nhấn Đăng ký để tạo tài khoản mới."* |
| Form: Tên đăng nhập, Email, Mật khẩu | *"Điền tên đăng nhập, email và mật khẩu. Tên đăng nhập dùng để đăng nhập lần sau."* |
| Tick checkbox điều khoản → click link **Điều khoản sử dụng** và **Chính sách quyền riêng tư** (mở tab, đóng lại) | *"Bắt buộc tick đồng ý Điều khoản và Chính sách quyền riêng tư trước khi tạo tài khoản."* |
| Nhấn **Tạo tài khoản** | *"Sau khi đăng ký thành công, bạn nhận 5 credits miễn phí — đủ để thử sinh khoảng 5 câu hỏi."* |
| (Nếu có Captcha) hiện reCAPTCHA | *"Hệ thống có thể yêu cầu xác minh Captcha để chống spam."* |

> **Lưu ý quay:** Không hiện mật khẩu thật; dùng tài khoản demo.

### 1.3 Đăng ký / Đăng nhập Google (3:15 – 4:15)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Trang đăng ký → **Đăng ký với Google** | *"Hoặc đăng ký nhanh bằng Google — không cần nhớ mật khẩu riêng."* |
| Chọn tài khoản Google | *"Lần đầu đăng nhập Google, hệ thống hiện trang đồng ý điều khoản. Đọc tóm tắt, tick đồng ý, nhấn Đồng ý & Tạo tài khoản."* |
| Trang `/auth/google/terms` → submit | *"Các lần sau chỉ cần chọn tài khoản Google là vào thẳng workspace."* |
| Đăng xuất → `/login` → **Tiếp tục với Google** | *"Đăng nhập Google tương tự đăng ký — dùng cho tài khoản đã liên kết."* |

### 1.4 Quên mật khẩu & Đăng xuất (4:15 – 5:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| `/login` → **Quên mật khẩu?** | *"Tài khoản email có thể khôi phục mật khẩu qua link gửi về email."* |
| Workspace → menu Avatar → **Đăng xuất** | *"Đăng xuất ở menu tài khoản góc phải navbar."* |

**Text overlay:** `PHẦN 2 — TRANG LÀM VIỆC (WORKSPACE)`

---

## PHẦN 2 — TỔNG QUAN WORKSPACE (5:00 – 7:00)

| Thời gian | Hình ảnh | Lời thoại |
|-----------|----------|-----------|
| 5:00–5:30 | Sau đăng nhập → `/` (workspace) | *"Đây là Trang làm việc — nơi bạn upload giáo trình, cấu hình Bloom và xem kết quả."* |
| 5:30–6:00 | Chỉ navbar: logo, **Trang chủ**, credits 🪙, menu ngôn ngữ, avatar | *"Thanh trên hiển thị số credits còn lại. Mỗi câu hỏi sinh ra trừ 1 credit. Hết credit thì vào trang Pricing để mua thêm."* |
| 6:00–6:30 | Chia layout: **cột trái** (Tạo bộ câu hỏi) + **cột phải** (Kết quả đã lưu) | *"Bên trái: cấu hình và sinh câu hỏi. Bên phải: lịch sử các lần sinh và xuất file."* |
| 6:30–7:00 | Click **Trang chủ** → landing; quay lại workspace | *"Trang chủ quay về landing giới thiệu. Bấm Bắt đầu ngay hoặc Workspace để quay lại."* |

---

## PHẦN 3 — TẢI GIÁO TRÌNH PDF (7:00 – 9:30)

### 3.1 Upload PDF mới (7:00 – 8:30)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Vùng **Upload PDF Mới** — kéo thả file | *"Cách 1: kéo thả file PDF vào vùng upload. Cách 2: click để chọn file từ máy."* |
| File được chọn → tên file hiện màu xanh | *"PDF phải có text chọn được — không phải ảnh scan. Dung lượng tối đa khoảng 50MB."* |
| Text overlay cảnh báo | *"PDF scan cần OCR trước, nếu không hệ thống không đọc được nội dung."* |

**Overlay gợi ý:** ❌ PDF scan · ✅ PDF có text

### 3.2 Chọn giáo trình đã lưu (8:30 – 9:30)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Dropdown **Chọn Giáo Trình Đã Lưu** | *"Lần sau không cần upload lại — chọn giáo trình đã lưu từ danh sách."* |
| Nút **✏️ đổi tên** giáo trình | *"Có thể đổi tên giáo trình cho dễ quản lý khi có nhiều môn."* |
| Badge **HOẶC** giữa 2 cách | *"Chỉ cần một trong hai: upload mới hoặc chọn giáo trình cũ — không bắt buộc cả hai."* |

**Text overlay:** `PHẦN 4 — CẤU HÌNH BLOOM & SINH CÂU HỎI`

---

## PHẦN 4 — CẤU HÌNH BLOOM & SINH CÂU HỎI (9:30 – 14:00)

### 4.1 Cấu hình 6 mức Bloom (9:30 – 11:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| 6 ô Bloom 1–6: **Số lượng câu hỏi** + **Số điểm / câu** | *"Mỗi mức Bloom có hai ô: số câu và điểm mỗi câu. Ví dụ Bloom 1 — Nhớ: 2 câu, 1 điểm/câu."* |
| Zoom từng mức (1–2 giây/mức) | *"Bloom 1 Nhớ — định nghĩa, liệt kê. Bloom 2 Hiểu — giải thích. Bloom 3 Vận dụng — tính toán, áp dụng. Bloom 4 Phân tích — so sánh. Bloom 5 Đánh giá — nhận xét. Bloom 6 Sáng tạo — thiết kế, đề xuất."* |
| Thanh **Tổng số câu** và **Tổng điểm** tự cập nhật | *"Hệ thống tự tính tổng câu và tổng điểm. Điểm chia theo bội 0,25."* |
| Nút **Tự động điền 10 điểm** | *"Nút Tự động điền 10 điểm giúp phân bổ nhanh ~10 điểm cho đề thi — Bloom thấp điểm cao hơn, Bloom cao thấp hơn."* |

**Ví dụ demo trên màn hình:**

| Mức Bloom | Số câu | Điểm/câu | Tổng điểm |
|-----------|--------|----------|-----------|
| Bloom 1 (Nhớ) | 2 | 1,0 | 2,0 |
| Bloom 2 (Hiểu) | 2 | 1,5 | 3,0 |
| Bloom 3 (Vận dụng) | 1 | 2,0 | 2,0 |
| Bloom 4 (Phân tích) | 1 | 2,0 | 2,0 |
| Bloom 5 (Đánh giá) | 1 | 0,5 | 0,5 |
| Bloom 6 (Sáng tạo) | 1 | 0,5 | 0,5 |
| **Tổng** | **8 câu = 8 credits** | | **10 điểm** |

### 4.2 Bắt đầu sinh câu hỏi (11:00 – 14:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Nhấn **PHÂN TÍCH & SINH CÂU HỎI** | *"Khi đã chọn PDF hoặc giáo trình và nhập ít nhất 1 mức Bloom, nhấn Phân tích & Sinh câu hỏi."* |
| Overlay tiến trình: % + thanh bar + message | *"Cửa sổ tiến trình hiện lên — không đóng tab trong lúc xử lý."* |
| Message: *Đang đọc giáo trình… trang X/Y* | *"Giai đoạn 1: AI đọc và trích xuất nội dung từ PDF — 10 đến 30 giây tùy file."* |
| Message: *Đang sinh câu X/Y (Bloom N)…* | *"Giai đoạn 2: sinh từng câu theo từng mức Bloom đã cấu hình."* |
| Message: *Hoàn tất! Đã sinh X/Y câu hỏi* → trang reload | *"Hoàn tất — trang tự tải lại, kết quả hiện bên phải. Credits bị trừ theo số câu thực tế sinh được."* |

> **Tip quay:** Cắt ghép — quay phần chờ ở tốc độ 4× hoặc jump cut khi % nhảy từ 0→100.

**Text overlay:** `PHẦN 5 — XEM KẾT QUẢ & XUẤT ĐỀ`

---

## PHẦN 5 — XEM KẾT QUẢ & XUẤT FILE (14:00 – 18:00)

### 5.1 Xem lịch sử & chi tiết câu hỏi (14:00 – 15:30)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Panel **Kết Quả Đã Lưu** — accordion từng lần sinh | *"Mỗi lần sinh là một batch — hiện thời gian, tên giáo trình, tổng câu."* |
| Mở accordion → bảng câu hỏi | *"Bảng gồm: câu hỏi, gợi ý đáp án, mức Bloom, điểm chất lượng 0–2, chương nguồn."* |
| Click 1 câu → modal chi tiết (nếu có) | *"Click câu hỏi để xem chi tiết đầy đủ và metadata AI đánh giá."* |
| Checkbox chọn câu → **Chọn tất cả / Bỏ chọn** | *"Tick chọn câu cần xuất — có thể chọn tất cả hoặc chỉ một phần."* |
| **Tải thêm** (nếu nhiều batch) | *"Nếu lịch sử dài, dùng Tải thêm để xem các lần sinh cũ hơn."* |

### 5.2 Xuất PDF (15:30 – 18:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Toolbar **Xuất PDF** — 2 nút: có đáp án / không đáp án | *"Chọn câu → xuất PDF. Có hai bản: đề có đáp án cho giảng viên, đề không đáp án cho sinh viên."* |
| Demo xuất **không đáp án** → file tải về → mở PDF | *"File PDF tải về mở bằng trình đọc PDF thông thường."* |
| Nút **2 bản PDF (có đáp án và không đáp án)** → modal **Xuất Đề Thi Tự Luận Chính Thức** | *"Xuất đề chính thức: điền thông tin trường, khoa, môn học, thời gian, học kỳ, năm học, ghi chú cho sinh viên."* |
| Điền form mẫu → **Tải 2 bản PDF (ZIP)** | *"Hệ thống tạo 2 PDF theo form đề chuẩn và đóng gói ZIP — một bản có đáp án, một bản không."* |
| Mở ZIP → show 2 file | *"Giảng viên in đề không đáp án; bản có đáp án dùng chấm bài."* |

**Text overlay:** `PHẦN 6 — CREDITS & THANH TOÁN`

---

## PHẦN 6 — CREDITS & THANH TOÁN (18:00 – 20:30)

| Thời gian | Hình ảnh | Lời thoại |
|-----------|----------|-----------|
| 18:00–18:30 | Click số credits trên navbar hoặc menu → `/pricing` | *"Vào Pricing khi hết credits hoặc cần mua thêm."* |
| 18:30–19:30 | Trang Pricing — các gói Starter / Basic / Pro | *"Chọn gói phù hợp — mỗi gói có số credits và giá khác nhau. Giá admin có thể cập nhật trên hệ thống."* |
| 19:30–20:00 | Chọn gói → **Thanh toán VNPay** (demo sandbox nếu có) | *"Thanh toán qua VNPay — chuyển sang cổng thanh toán, hoàn tất giao dịch."* |
| 20:00–20:30 | Quay lại → credits tăng; `/payment/history` (nếu có) | *"Credits cộng ngay sau thanh toán thành công. Xem lịch sử giao dịch tại Payment History."* |

> **Lưu ý quay:** Dùng môi trường sandbox VNPay; che thông tin thẻ thật.

---

## PHẦN 7 — TÀI KHOẢN & HỖ TRỢ (20:30 – 22:30)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Menu Avatar → **Đổi mật khẩu** (`/change-password`) | *"Tài khoản email có thể đổi mật khẩu tại đây. Tài khoản Google không cần đổi mật khẩu trên TEXTQAI."* |
| Footer landing → **Hướng dẫn sử dụng** (`/user-guide`) | *"User Guide tóm tắt toàn bộ quy trình — có bản Việt và Anh."* |
| **Support** — FAQ, email, form phản hồi | *"Gặp sự cố: xem FAQ hoặc gửi phản hồi qua form Support."* |
| Links pháp lý: Privacy, Terms, Payment Policy, AI Policy | *"Các chính sách pháp lý và AI được công khai minh bạch."* |

---

## PHẦN 8 — MẸO & LỖI THƯỜNG GẶP (22:30 – 24:00)

| Tình huống | Lời thoại |
|------------|-----------|
| PDF không xử lý được | *"Kiểm tra PDF có text không. Thử file khác hoặc OCR trước."* |
| Credits trừ nhưng không có kết quả | *"Liên hệ Support kèm thời gian sinh — admin có thể hoàn credits."* |
| Câu hỏi sai mức Bloom | *"AI đạt khoảng 70–80% độ chính xác phân loại Bloom — nên rà soát trước khi ra đề."* |
| Giáo trình tiếng Anh | *"Hệ thống hỗ trợ cả tiếng Việt và tiếng Anh."* |
| Dùng trên app mobile | *"Có app Android/iOS bọc WebView — quy trình giống website, đổi ngôn ngữ ở header landing."* |

---

## PHẦN 9 — KẾT THÚC (24:00 – 25:00)

| Hình ảnh | Lời thoại |
|----------|-----------|
| Tóm tắt 4 bước (text overlay): **① Đăng ký → ② Upload PDF → ③ Cấu hình Bloom → ④ Xuất đề** | *"Tóm lại: đăng ký, upload giáo trình, cấu hình Bloom, sinh câu hỏi và xuất PDF. Chúc bạn soạn đề hiệu quả với TEXTQAI!"* |
| Landing + logo + URL website | *"Truy cập website và bắt đầu với 5 credits miễn phí. Hẹn gặp lại!"* |

---

## Gợi ý chia clip ngắn (TikTok / Reels / YouTube Shorts)

| Clip | Nội dung | Thời lượng |
|------|----------|------------|
| **Clip 1** | Đăng ký + 5 credits free | 2–3 phút |
| **Clip 2** | Upload PDF + cấu hình Bloom + sinh câu | 4–5 phút |
| **Clip 3** | Xem kết quả + xuất 2 PDF ZIP | 3–4 phút |
| **Clip 4** | Mua credits VNPay | 2–3 phút |

---

## Checklist trước khi quay

- [ ] Tài khoản demo có ≥ 15 credits
- [ ] PDF mẫu sẵn (CSDL, Toán, Luật… — tên dễ nhận diện)
- [ ] Xóa lịch sử sinh cũ hoặc dùng tài khoản sạch
- [ ] Trình duyệt zoom 100%, ẩn thanh bookmark
- [ ] Tắt thông báo Windows / macOS
- [ ] Chuẩn bị script lỗi: 1 PDF scan (demo cảnh báo)
- [ ] OBS / Camtasia: vùng quay 1920×1080, con trỏ to, click chậm
- [ ] Ghi âm mic riêng, giảm tiếng ồn phòng

---

## Phụ lục — Bảng lời thoại nhanh (Teleprompter)

```
[MỞ] TEXTQAI — sinh câu hỏi Bloom từ PDF giáo trình.

[ĐK] Đăng ký email hoặc Google. Tick điều khoản. Nhận 5 credits free.

[WS] Workspace: trái = sinh đề, phải = kết quả. Credits góc phải.

[UP] Upload PDF có text HOẶC chọn giáo trình đã lưu.

[BL] Cấu hình Bloom 1–6: số câu + điểm. Nút Tự động điền 10 điểm.

[SINH] Phân tích & Sinh câu hỏi. Chờ tiến trình. 1 câu = 1 credit.

[XEM] Kết quả đã lưu → mở batch → chọn câu → xuất PDF.

[ZIP] Xuất đề chính thức: điền thông tin trường/môn → tải ZIP 2 PDF.

[MUA] Pricing → VNPay → credits cộng ngay.

[KẾT] Đăng ký → Upload → Bloom → Xuất đề. Cảm ơn!
```

---

## Tham chiếu tài liệu liên quan

| File | Mô tả |
|------|-------|
| [user_guide.md](./user_guide.md) | Hướng dẫn sử dụng ngắn gọn (VI/EN) |
| [install_guide.md](./install_guide.md) | Hướng dẫn cài đặt hệ thống |
