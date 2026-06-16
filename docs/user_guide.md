# Hướng Dẫn Sử Dụng TEXTQAI | User Guide

> **Phiên bản / Version:** 1.0 &nbsp;|&nbsp; **Cập nhật / Updated:** 06/2026

---

## 🇻🇳 TIẾNG VIỆT

### Mục lục
1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Đăng ký & Đăng nhập](#2-đăng-ký--đăng-nhập)
3. [Tải tài liệu PDF](#3-tải-tài-liệu-pdf)
4. [Sinh câu hỏi / trả lời](#4-sinh-câu-hỏi--trả-lời)
5. [Xem kết quả](#5-xem-kết-quả)
6. [Credits & Thanh toán](#6-credits--thanh-toán)
7. [Cài đặt tài khoản](#7-cài-đặt-tài-khoản)
8. [Câu hỏi thường gặp](#8-câu-hỏi-thường-gặp)

---

### 1. Tổng quan hệ thống

**TEXTQAI** là nền tảng tự động sinh câu hỏi và trả lời từ tài liệu PDF theo **Thang phân loại Bloom** (6 cấp độ nhận thức):

| Cấp độ | Tên | Ví dụ loại câu hỏi |
|--------|-----|-------------------|
| Bloom 1 | Nhớ (Remember) | Định nghĩa, liệt kê |
| Bloom 2 | Hiểu (Understand) | Giải thích, mô tả |
| Bloom 3 | Áp dụng (Apply) | Tính toán, sử dụng |
| Bloom 4 | Phân tích (Analyze) | So sánh, phân biệt |
| Bloom 5 | Đánh giá (Evaluate) | Nhận xét, đánh giá |
| Bloom 6 | Sáng tạo (Create) | Đề xuất, thiết kế |

Hệ thống sử dụng **pipeline 3 tác nhân AI**:
- **Agent 1** – Trích xuất nội dung chương/mục từ PDF
- **Agent 2** – Sinh câu hỏi & trả lời theo từng cấp Bloom
- **Agent 3** – Đánh giá chất lượng và chấm điểm

---

### 2. Đăng ký & Đăng nhập

#### Đăng ký tài khoản mới
1. Truy cập trang chủ → nhấn **Đăng ký**
2. Điền **Tên tài khoản**, **Email**, **Mật khẩu**
3. Tích vào ô **"Tôi đồng ý Điều khoản dịch vụ và Chính sách quyền riêng tư"**
4. Nhấn **Đăng ký** — tài khoản được tạo ngay, nhận **5 credits miễn phí**

#### Đăng nhập bằng Google
1. Nhấn nút **"Đăng nhập bằng Google"**
2. Chọn tài khoản Google
3. **Lần đầu tiên**: đọc và đồng ý Điều khoản → nhấn **"Đồng ý & Tạo tài khoản"**
4. Lần tiếp theo: đăng nhập thẳng

> 💡 **Mới đăng ký được 5 credits miễn phí** — đủ để thử sinh ~5 câu hỏi.

---

### 3. Tải tài liệu PDF

1. Sau khi đăng nhập, vào **Trang làm việc** (workspace)
2. Nhấn **"Tải lên tài liệu"** hoặc kéo thả file PDF vào vùng upload
3. Đặt tên tài liệu (tuỳ chọn)
4. Chờ hệ thống xử lý và trích xuất nội dung (~10-30 giây tuỳ file)

> ⚠️ **Lưu ý:**
> - Chỉ hỗ trợ file **PDF** (tối đa 50MB)
> - PDF cần có text (không phải ảnh scan)
> - Một tài khoản có thể lưu nhiều tài liệu

---

### 4. Sinh câu hỏi / trả lời

1. Chọn **tài liệu** từ danh sách bên trái
2. Chọn **Chương/Mục** muốn sinh câu hỏi
3. Chọn **cấp độ Bloom** (1–6, có thể chọn nhiều)
4. Nhập **số câu hỏi** mỗi cấp độ (mặc định: 2)
5. Nhấn **"Sinh câu hỏi"**
6. Hệ thống xử lý trong nền — thanh tiến trình hiển thị trạng thái
7. Kết quả xuất hiện tự động khi hoàn tất

> 💰 **Chi phí credits:**
> - Mỗi câu hỏi được sinh = **1 credit**
> - Ví dụ: 6 cấp Bloom × 2 câu = **12 credits**

---

### 5. Xem kết quả

Sau khi sinh xong, kết quả hiển thị gồm:

| Cột | Nội dung |
|-----|----------|
| Câu hỏi | Nội dung câu hỏi |
| Trả lời | Gợi ý đáp án |
| Bloom | Cấp độ nhận thức |
| Điểm | Điểm đánh giá chất lượng (0–2) |
| Chương | Nguồn chương được trích xuất |

#### Xuất kết quả
- Nhấn **"Xuất CSV"** để tải về file Excel/CSV
- Nhấn **"Xuất PDF"** để tải về file PDF (nếu có)
- Copy trực tiếp từ bảng kết quả

---

### 6. Credits & Thanh toán

#### Xem số credits hiện có
- Hiển thị ở góc trên phải navbar (biểu tượng 🪙)

#### Mua thêm credits
1. Nhấn vào số credits hoặc vào **Pricing**
2. Chọn gói phù hợp
3. Thanh toán qua **SePay / VNPay**
4. Credits cộng vào tài khoản ngay sau khi thanh toán thành công

| Gói | Credits | Giá |
|-----|---------|-----|
| Starter | 50 | 13,000đ |
| Basic | 200 | 45,000đ |
| Pro | 500 | 99,000đ |

---

### 7. Cài đặt tài khoản

- **Đổi mật khẩu**: Trang chủ → menu Avatar → **Đổi mật khẩu**
- **Đăng xuất**: Menu Avatar → **Đăng xuất**
- **Xóa tài khoản**: Liên hệ hỗ trợ tại trang [Support](/support)

---

### 8. Câu hỏi thường gặp

**Q: PDF của tôi không được xử lý?**  
A: Kiểm tra PDF có chứa text thật không (không phải ảnh scan). Thử dùng công cụ OCR trước.

**Q: Credits bị trừ nhưng không có kết quả?**  
A: Hệ thống có thể gặp lỗi tạm thời. Liên hệ hỗ trợ qua email để được hoàn credits.

**Q: Câu hỏi sinh ra không đúng cấp Bloom?**  
A: AI có thể nhầm cấp độ trong một số trường hợp. Hệ thống đạt ~70-80% độ chính xác phân loại Bloom.

**Q: Có thể dùng tài liệu tiếng Anh không?**  
A: Có, hệ thống hỗ trợ cả tiếng Việt và tiếng Anh.

---
---

## 🇬🇧 ENGLISH

### Table of Contents
1. [System Overview](#1-system-overview)
2. [Register & Login](#2-register--login)
3. [Upload PDF Document](#3-upload-pdf-document)
4. [Generate Q&A](#4-generate-qa)
5. [View Results](#5-view-results)
6. [Credits & Payment](#6-credits--payment)
7. [Account Settings](#7-account-settings)
8. [FAQ](#8-faq)

---

### 1. System Overview

**TEXTQAI** automatically generates questions and answers from PDF documents following **Bloom's Taxonomy** (6 cognitive levels):

| Level | Name | Example Question Types |
|-------|------|----------------------|
| Bloom 1 | Remember | Definitions, listing facts |
| Bloom 2 | Understand | Explain, describe |
| Bloom 3 | Apply | Calculate, use concepts |
| Bloom 4 | Analyze | Compare, distinguish |
| Bloom 5 | Evaluate | Critique, assess |
| Bloom 6 | Create | Propose, design |

The system uses a **3-agent AI pipeline**:
- **Agent 1** – Extracts chapters/sections from the PDF
- **Agent 2** – Generates Q&A pairs per Bloom level
- **Agent 3** – Evaluates quality and scores each pair

---

### 2. Register & Login

#### Create a New Account
1. Go to homepage → click **Register**
2. Enter **Username**, **Email**, **Password**
3. Check **"I agree to the Terms of Service and Privacy Policy"**
4. Click **Register** — account created instantly with **5 free credits**

#### Login with Google
1. Click **"Login with Google"**
2. Select your Google account
3. **First time only**: read and agree to Terms → click **"Agree & Create Account"**
4. Subsequent logins: direct access

> 💡 **New accounts get 5 free credits** — enough to try generating ~5 questions.

---

### 3. Upload PDF Document

1. After logging in, go to **Workspace**
2. Click **"Upload Document"** or drag and drop a PDF file
3. Add a document name (optional)
4. Wait for the system to process and extract content (~10–30 seconds)

> ⚠️ **Notes:**
> - Only **PDF** files supported (max 50MB)
> - PDF must contain selectable text (not scanned images)
> - Multiple documents can be stored per account

---

### 4. Generate Q&A

1. Select a **document** from the left panel
2. Select a **Chapter/Section** to generate questions from
3. Select **Bloom level(s)** (1–6, multiple allowed)
4. Enter **number of questions** per level (default: 2)
5. Click **"Generate Questions"**
6. The system processes in the background — a progress bar shows status
7. Results appear automatically when complete

> 💰 **Credit cost:**
> - Each generated question = **1 credit**
> - Example: 6 Bloom levels × 2 questions = **12 credits**

---

### 5. View Results

After generation, results show:

| Column | Content |
|--------|---------|
| Question | Question text |
| Answer | Suggested answer |
| Bloom | Cognitive level |
| Score | Quality score (0–2) |
| Chapter | Source chapter |

#### Export Results
- Click **"Export CSV"** to download as spreadsheet
- Click **"Export PDF"** to download as PDF (if available)
- Copy directly from the results table

---

### 6. Credits & Payment

#### Check Current Credits
- Displayed in the top-right navbar (🪙 icon)

#### Purchase Credits
1. Click your credit count or go to **Pricing**
2. Choose a package
3. Pay via **SePay / VNPay**
4. Credits are added immediately after successful payment

| Package | Credits | Price |
|---------|---------|-------|
| Starter | 50 | 13,000 VND |
| Basic | 200 | 45,000 VND |
| Pro | 500 | 99,000 VND |

---

### 7. Account Settings

- **Change Password**: Homepage → Avatar menu → **Change Password**
- **Logout**: Avatar menu → **Logout**
- **Delete Account**: Contact support at [Support](/support)

---

### 8. FAQ

**Q: My PDF isn't being processed?**  
A: Verify the PDF contains real text (not scanned images). Try an OCR tool first.

**Q: Credits were deducted but no results appeared?**  
A: The system may have encountered a temporary error. Contact support for a credit refund.

**Q: Generated questions don't match the expected Bloom level?**  
A: AI classification has ~70-80% accuracy. Some misclassification can occur naturally.

**Q: Can I use English-language documents?**  
A: Yes, the system supports both Vietnamese and English documents.
