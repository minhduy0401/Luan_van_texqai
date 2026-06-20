# Hướng dẫn chạy thực nghiệm TEXTQAI

Tài liệu này hướng dẫn **chuẩn bị môi trường, chạy script, đầu vào lấy ở đâu và đầu ra sinh ra gì** cho các script trong `experiment/` — phục vụ luận văn (BLEU, Attribution Accuracy, ACC₂LLM / ACC₃LLM).

> **Phương pháp luận chi tiết** (mục tiêu, công thức, kết quả mẫu): xem [`experiment/exp1.md`](../experiment/exp1.md) và [`experiment/exp2.md`](../experiment/exp2.md).

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Điều kiện tiên quyết](#2-điều-kiện-tiên-quyết)
3. [Cấu trúc thư mục](#3-cấu-trúc-thư-mục)
4. [Chuẩn bị giáo trình PDF](#4-chuẩn-bị-giáo-trình-pdf)
5. [Cấu hình API key & model](#5-cấu-hình-api-key--model)
6. [Chạy thử nhanh (smoke test)](#6-chạy-thử-nhanh-smoke-test)
7. [Thực nghiệm 1 – BLEU & Attribution](#7-thực-nghiệm-1--bleu--attribution)
8. [Thực nghiệm 2 – Độ chính xác Bloom](#8-thực-nghiệm-2--độ-chính-xác-bloom)
9. [Kết quả đầu ra](#9-kết-quả-đầu-ra)
10. [Thời gian & chi phí ước tính](#10-thời-gian--chi-phí-ước-tính)
11. [Xử lý lỗi thường gặp](#11-xử-lý-lỗi-thường-gặp)
12. [Tóm tắt nhanh](#12-tóm-tắt-nhanh)
13. [English summary](#13-english-summary)

---

## 1. Tổng quan

| Script | Mục đích | Quy mô mặc định |
|--------|----------|-----------------|
| `experiment/run_any_pdf.py` | Kiểm tra pipeline trên **một** PDF bất kỳ | 2 câu / 1 mức Bloom |
| `experiment/experiment_1_chapter_bleu.py` | So sánh **3 LLM** — BLEU & Chapter Attribution | 144 câu (3 model × 4 PDF × 12 câu) |
| `experiment/experiment_2_bloom_accuracy.py` | Đánh giá nhãn Bloom bằng **3 LLM độc lập** | 120 câu sinh + 360 lần phân loại |

**Luồng khuyến nghị:**

```
Cài app (install_guide.md) → Cấu hình OpenRouter → Copy PDF → run_any_pdf.py → Exp 1 → Exp 2
```

**Luồng dữ liệu:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ĐẦU VÀO (bạn chuẩn bị)                                                │
│  • PDF giáo trình (.pdf) → copy vào experiment/                         │
│  • OpenRouter API key → Admin → Cài đặt hệ thống                       │
│  • App + DB đã init (PostgreSQL/MySQL + instance/bootstrap.json)       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
 run_any_pdf.py      experiment_1_chapter_bleu.py   experiment_2_bloom_accuracy.py
 (1 PDF, smoke)      (3 model × 4 PDF × 12 câu)       (120 câu + 360 lần phân loại)
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ĐẦU RA                                                                 │
│  • Terminal: log tiến trình, Q&A mẫu, tóm tắt chỉ số                      │
│  • experiment/results/exp*_raw_<timestamp>.csv                          │
│  • experiment/results/exp*_raw_<timestamp>_excel.csv  (UTF-8 BOM)       │
│  • experiment/results/exp*_report_<timestamp>.md                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Điều kiện tiên quyết

### 2.1. Hệ thống đã chạy được

Hoàn tất các bước trong [`docs/install_guide.md`](install_guide.md):

- Python 3.10+ và `pip install -r requirements.txt`
- MySQL (XAMPP) hoặc PostgreSQL + `instance/bootstrap.json`
- `python init_db.py` thành công
- `python app.py` mở được trang web

### 2.2. Thư viện thí nghiệm

Đã có trong `requirements.txt`:

| Gói | Vai trò |
|-----|---------|
| **NLTK** | Tính BLEU (Exp 1) — script tự tải `punkt` lần đầu |
| **pdfplumber** | Trích xuất văn bản PDF |
| **openai** | Gọi OpenRouter API (Exp 2 đánh giá Bloom) |

Cài lại nếu thiếu:

```powershell
cd C:\duong\dan\Luanvan_Bloom
pip install -r requirements.txt
```

### 2.3. Cấu hình Bloom (hard-code trong script)

Cả 3 script dùng **6 mức Bloom** (B1–B6). Số câu mỗi mức được cố định trong code:

| Script | Câu / mức Bloom / PDF | Tổng câu / PDF |
|--------|----------------------|----------------|
| `run_any_pdf.py` | Tùy `--count` (mặc định 2) | Chỉ **1** mức (`--bloom`, mặc định 3) |
| Exp 1 | 2 | 12 (= 2 × 6) |
| Exp 2 | 5 | 30 (= 5 × 6) |

---

## 3. Cấu trúc thư mục

```
experiment/
├── experiment_1_chapter_bleu.py   # Thực nghiệm 1
├── experiment_2_bloom_accuracy.py   # Thực nghiệm 2
├── run_any_pdf.py                 # Smoke test 1 PDF
├── experiment_runtime.py          # Đồng bộ cấu hình AI từ app chính
├── pdf_paths.py                   # Tham số --pdf / --pdf-dir
├── csv_export.py                  # Xuất CSV + bản Excel
├── exp1.md                        # Mô tả phương pháp Exp 1
├── exp2.md                        # Mô tả phương pháp Exp 2
├── *.pdf                          # Giáo trình (bạn tự copy vào đây)
├── exp1_temp.db                   # SQLite tạm (tự tạo khi chạy Exp 1)
├── exp2_temp.db                   # SQLite tạm (tự tạo khi chạy Exp 2)
├── any_pdf_temp.db                # SQLite tạm (smoke test)
└── results/
    ├── exp1_raw_<timestamp>.csv
    ├── exp1_raw_<timestamp>_excel.csv
    ├── exp1_report_<timestamp>.md
    ├── exp2_raw_<timestamp>.csv
    └── exp2_report_<timestamp>.md
```

> **Lưu ý:** File `.pdf` giáo trình **không commit** lên Git (thường nặng / bản quyền). Mỗi máy cần copy PDF vào `experiment/` trước khi chạy.

---

## 4. Chuẩn bị giáo trình PDF

### 4.1. Thực nghiệm đầy đủ (Exp 1 & 2)

| Thuộc tính | Chi tiết |
|------------|----------|
| **Lấy ở đâu** | Bạn tự sưu tập / tải giáo trình đại học |
| **Lĩnh vực gợi ý** | AI, CNPM, CSDL, Mạng máy tính |
| **Đặt ở đâu** | Thư mục `experiment/` |
| **Số lượng** | **4 file** `*.pdf` (Exp 1 & 2 tự quét tất cả) |
| **Tên file** | Tùy ý — tên không đuôi → cột `pdf` trong CSV |

Copy **4 file PDF** vào `experiment/`. Script lấy tất cả `*.pdf`, sắp xếp A→Z.

**Yêu cầu PDF:**

- Có **văn bản copy được** (không phải scan ảnh thuần). Nếu scan → dùng `--ocr` ở smoke test hoặc bật OCR trong Admin.
- Có cấu trúc **chương / mục** rõ (tiêu đề) để pipeline tách section.

Exp 1 và Exp 2 **không có tham số dòng lệnh** — chỉ quét `experiment/*.pdf`.

### 4.2. Kiểm tra đã có PDF

```powershell
cd C:\duong\dan\Luanvan_Bloom
dir experiment\*.pdf
```

Phải thấy ít nhất 1 file. Exp 1/2 mặc định cần **4 PDF** — nếu ít hơn, script vẫn chạy nhưng quy mô câu hỏi giảm theo số PDF thực tế.

### 4.3. Chỉ định PDF / thư mục khác (chỉ smoke test)

```powershell
python experiment/run_any_pdf.py --pdf "D:\TaiLieu\giao_trinh_ai.pdf"
python experiment/run_any_pdf.py --pdf-dir "D:\TaiLieu\GT"
```

---

## 5. Cấu hình API key & model

### 5.1. OpenRouter API key

| Thuộc tính | Chi tiết |
|------------|----------|
| **Lấy ở đâu** | [openrouter.ai](https://openrouter.ai/) → tạo tài khoản → API Keys |
| **Lưu trong app** | Admin → **Cài đặt hệ thống** → AI / OpenRouter → `openrouter_api_key` |
| **Lưu trong DB** | Bảng `system_settings`, key `openrouter_api_key` |
| **Script đọc** | `experiment/experiment_runtime.py` copy từ DB app chính sang SQLite tạm |

Cấu hình trong app:

1. Chạy `python app.py`
2. Đăng nhập **Admin → Cài đặt hệ thống**
3. Mục **AI / OpenRouter** → dán `openrouter_api_key`
4. **Lưu cài đặt**
5. Nạp credit (Exp 1 + Exp 2 tốn **hàng trăm lượt gọi API**)

Module `experiment/experiment_runtime.py` thực hiện:

1. Load app Flask chính (`app.py`) — cần `bootstrap.json` + DB đúng
2. Đọc `system_settings` (OpenRouter key, model, provider…)
3. Ghi sang SQLite tạm của thí nghiệm

**Điều kiện:** ít nhất một trong các key sau có giá trị trong Admin:

- `openrouter_api_key` *(khuyến nghị)*
- `openai_api_key`
- `gemini_api_key`

Nếu thiếu:

```
Chưa có API key trong Admin → Cài đặt (system_settings).
```

Script **không** đọc file `.env` trực tiếp — luôn đồng bộ qua DB app chính.

### 5.2. Model AI

| Thiết lập | Nguồn | Ghi chú |
|-----------|-------|---------|
| Model sinh Q&A (smoke test) | Admin → Cài đặt hoặc `config.py` | Dùng `config.QUESTION_MODEL` |
| Model Exp 1 | Cố định trong script | 3 model so sánh (mục 7) |
| Model sinh Exp 2 | Cố định | `google/gemini-2.5-flash-lite` |
| Model đánh giá Exp 2 | Cố định | Cùng 3 model Exp 1 |

---

## 6. Chạy thử nhanh (smoke test)

Dùng trước Exp 1/2 để xác nhận PDF đọc được và pipeline sinh câu OK.

### 6.1. Đầu vào

| # | Đầu vào | Bắt buộc | Lấy ở đâu |
|---|---------|----------|-----------|
| 1 | **1 file PDF** | Có | `--pdf "đường/dẫn/file.pdf"` hoặc copy vào `experiment/` |
| 2 | **OpenRouter API key** | Có | Admin → Cài đặt (mục 5) |
| 3 | **DB app chính** | Có | PostgreSQL/MySQL + `instance/bootstrap.json` |
| 4 | `--bloom` (1–6) | Không | Mặc định `3` |
| 5 | `--count` | Không | Mặc định `2` |
| 6 | `--points` | Không | Mặc định `1.5` |
| 7 | `--ocr` | Không | Bật OCR nếu PDF scan |

### 6.2. Lệnh chạy

```powershell
cd C:\duong\dan\Luanvan_Bloom

# Mặc định: PDF đầu tiên trong experiment/, Bloom 3, 2 câu
python experiment/run_any_pdf.py

# Tùy chọn
python experiment/run_any_pdf.py --pdf "experiment\giao_trinh_ai.pdf" --bloom 4 --count 3 --ocr
```

| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `--pdf PATH` | — | PDF cụ thể (lặp được nhiều lần) |
| `--pdf-dir DIR` | `experiment/` | Thư mục chứa PDF |
| `--bloom 1-6` | `3` | Mức Bloom |
| `--count N` | `2` | Số câu sinh |
| `--points X` | `1.5` | Điểm mỗi câu |
| `--ocr` | tắt | Bật OCR khi PDF là scan |

### 6.3. Xử lý & đầu ra

1. Đọc bytes PDF → trích text (`pdfplumber`, hoặc OCR nếu `--ocr`)
2. Phân tách chương/mục → chạy pipeline 3 Agent
3. SQLite tạm: `experiment/any_pdf_temp.db`

| Đầu ra | Vị trí | Nội dung |
|--------|--------|----------|
| **Log terminal** | PowerShell | Số mục parse, Q/A từng câu (rút gọn) |
| **Exit code** | — | `0` nếu sinh ≥ 1 câu; `1` nếu lỗi |
| **CSV / MD** | — | **Không tạo** |

Nếu thấy `Kết quả: 2/2 câu trong 45s` và in được Q/A → pipeline OK. Nếu `0 câu` → xem mục 11.

---

## 7. Thực nghiệm 1 – BLEU & Attribution

### 7.1. Mục tiêu

- Sinh câu hỏi / đáp án bằng **3 model**:
  - `google/gemini-2.5-flash-lite`
  - `deepseek/deepseek-chat-v3-0324`
  - `openai/gpt-4o-mini`
- Tính **BLEU-1, BLEU-2, BLEU-4** (đáp án so với chương nguồn)
- Tính **Chapter Attribution Accuracy** (đáp án có bám đúng chương nguồn không)

### 7.2. Đầu vào

| # | Đầu vào | Bắt buộc | Lấy ở đâu |
|---|---------|----------|-----------|
| 1 | **4 file PDF** | Có | `experiment/*.pdf` |
| 2 | **OpenRouter API key** | Có | Admin → Cài đặt |
| 3 | **3 model AI** | Cố định | Trong script `MODELS` |
| 4 | **Cấu hình Bloom** | Cố định | 2 câu × 6 mức = 12 câu/PDF/model |
| 5 | **Pipeline 3 Agent** | Tự động | `services/pipeline.py` |

**Quy mô mục tiêu:** 3 model × 4 PDF × 12 câu = **144 dòng** CSV.

### 7.3. Lệnh chạy

```powershell
cd C:\duong\dan\Luanvan_Bloom
python experiment/experiment_1_chapter_bleu.py
```

Chạy từ thư mục `experiment/` cũng được:

```powershell
cd experiment
python experiment_1_chapter_bleu.py
```

### 7.4. Quy trình tự động

```
Với mỗi model:
  Với mỗi PDF:
    1. Trích text PDF → phân chương/mục
    2. Pipeline sinh 12 Q&A (ghi chapter_key, section_content)
    3. Với mỗi câu:
       - BLEU-1/2/4: đáp án vs chương nguồn (top-7 câu liên quan)
       - BLEU-4 vs TẤT CẢ chương → tìm best_bleu_chapter
       - is_correct = (best_bleu_chapter == source_chapter)
    4. Ghi tăng dần vào CSV (mất điện vẫn giữ dữ liệu)
    5. Tạo báo cáo Markdown tổng hợp
```

Terminal in dạng:

```
[1/3] MODEL: google/gemini-2.5-flash-lite
  [1/4] Giáo trình: giao_trinh_ai
  ✓ Đọc PDF xong: 125,430 ký tự
  ...
  💾 CSV (ghi tăng dần): experiment/results/exp1_raw_20260617_120747.csv
```

Giữ cửa sổ PowerShell mở; **không tắt** giữa chừng nếu có thể tránh.

### 7.5. Đầu ra

| File | Đường dẫn | Mô tả |
|------|-----------|-------|
| **CSV raw** | `experiment/results/exp1_raw_YYYYMMDD_HHMMSS.csv` | 144 dòng × 22 cột |
| **CSV Excel** | `..._excel.csv` | UTF-8 BOM — mở Excel |
| **Báo cáo MD** | `exp1_report_YYYYMMDD_HHMMSS.md` | BLEU/Attribution theo model, Bloom, PDF |
| **Log terminal** | PowerShell | BLEU từng câu, ✅/❌ attribution |

**Cột quan trọng:** `bleu4_ans_chapter`, `best_bleu_chapter`, `is_correct`, `question`, `answer`.

**Chỉ số tổng hợp:**

- **Attribution Accuracy** = % dòng có `is_correct = True`
- **BLEU trung bình** theo model / mức Bloom

---

## 8. Thực nghiệm 2 – Độ chính xác Bloom

### 8.1. Mục tiêu

1. Sinh **120 câu** (4 PDF × 30 câu) bằng **Gemini 2.5 Flash Lite**
2. Gửi từng Q&A cho **3 LLM đánh giá** (cùng bộ model Exp 1)
3. Tính **ACC₂LLM** (≥ 2/3 LLM đồng ý) và **ACC₃LLM** (3/3 đồng ý)

### 8.2. Đầu vào

| # | Đầu vào | Bắt buộc | Lấy ở đâu |
|---|---------|----------|-----------|
| 1 | **4 file PDF** | Có | `experiment/*.pdf` (giống Exp 1) |
| 2 | **OpenRouter API key** | Có | Admin → Cài đặt |
| 3 | **Model sinh Q&A** | Cố định | `google/gemini-2.5-flash-lite` |
| 4 | **3 model đánh giá** | Cố định | Gemini, DeepSeek, GPT-4o-mini |
| 5 | **Cấu hình Bloom** | Cố định | 5 câu × 6 mức = 30 câu/PDF |

**Quy mô mục tiêu:** 120 dòng CSV + 360 lượt gọi LLM phân loại.

### 8.3. Lệnh chạy

```powershell
cd C:\duong\dan\Luanvan_Bloom
python experiment/experiment_2_bloom_accuracy.py
```

> **Khuyến nghị:** Chạy **sau Exp 1** khi đã xác nhận pipeline ổn định.

### 8.4. Quy trình tự động

```
Với mỗi PDF:
  1. Pipeline sinh 30 Q&A (nhãn Bloom hệ thống → sys_bloom_int)
  2. Với mỗi câu:
     - Gửi Q&A cho 3 LLM (temperature=0) → bloom_pred_0/1/2
     - n_agree, is_2llm, is_3llm
  3. Ghi tăng dần CSV → xuất báo cáo .md
```

Cuối run in tóm tắt:

```
ACC₂LLM : 85/120 = 70.8%
ACC₃LLM : 55/120 = 45.8%
```

### 8.5. Đầu ra

| File | Đường dẫn | Mô tả |
|------|-----------|-------|
| **CSV raw** | `experiment/results/exp2_raw_YYYYMMDD_HHMMSS.csv` | 120 dòng |
| **CSV Excel** | `..._excel.csv` | Bản Excel |
| **Báo cáo MD** | `exp2_report_YYYYMMDD_HHMMSS.md` | ACC₂LLM, ACC₃LLM, phân tích Bloom |
| **Log terminal** | PowerShell | Tóm tắt ACC cuối run |

**Cột quan trọng:** `sys_bloom_int`, `bloom_pred_0/1/2`, `n_agree`, `is_2llm`, `is_3llm`.

**Chỉ số tổng hợp:**

$$\text{ACC}_{2\text{LLM}} = \frac{\#\{is\_2llm = True\}}{N} \qquad \text{ACC}_{3\text{LLM}} = \frac{\#\{is\_3llm = True\}}{N}$$

---

## 9. Kết quả đầu ra

Tất cả file kết quả nằm trong `experiment/results/`.

### 9.1. Exp 1 — file & báo cáo

| File | Nội dung |
|------|----------|
| `exp1_raw_<timestamp>.csv` | 144 dòng (nếu đủ PDF), 22 cột — Q&A đầy đủ, điểm BLEU |
| `exp1_raw_<timestamp>_excel.csv` | Bản UTF-8 BOM — mở trực tiếp bằng Excel |
| `exp1_report_<timestamp>.md` | Bảng tổng hợp theo model / Bloom; danh sách attribution sai |

### 9.2. Exp 2 — file & báo cáo

| File | Nội dung |
|------|----------|
| `exp2_raw_<timestamp>.csv` | 120 dòng — nhãn hệ thống vs 3 LLM |
| `exp2_raw_<timestamp>_excel.csv` | Bản Excel |
| `exp2_report_<timestamp>.md` | ACC₂LLM, ACC₃LLM; phân tích theo Bloom và PDF |

### 9.3. Bảng cột CSV — Exp 1 (22 cột)

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `model` | text | Tên đầy đủ model OpenRouter |
| `model_short` | text | Tên rút gọn |
| `pdf` | text | Tên file PDF không đuôi |
| `bloom_level` | text | VD: `Bloom 4 (Phân tích)` |
| `bloom_short` | text | VD: `B4` |
| `source_chapter` | text | Chương nguồn pipeline chọn |
| `section_info` | text | Mục con trong chương |
| `bleu1_ans_chapter` | float 0–1 | BLEU-1 đáp án vs chương nguồn |
| `bleu2_ans_chapter` | float 0–1 | BLEU-2 đáp án vs chương nguồn |
| `bleu4_ans_chapter` | float 0–1 | BLEU-4 đáp án vs chương nguồn |
| `best_bleu_chapter` | text | Chương có BLEU-4 cao nhất |
| `best_bleu_score` | float 0–1 | Điểm BLEU-4 của chương đó |
| `is_correct` | bool | Attribution đúng chương nguồn |
| `bleu4_ans_section` | float 0–1 | BLEU-4 đáp án vs mục lẻ |
| `bleu4_q_chapter` | float 0–1 | BLEU-4 câu hỏi vs chương nguồn |
| `answer_words` | int | Số từ trong đáp án |
| `question_words` | int | Số từ trong câu hỏi |
| `chapter_words` | int | Số từ chương nguồn |
| `section_words` | int | Số từ mục nguồn |
| `process_time_s` | float | Thời gian sinh câu (giây) |
| `total_points` | float | Điểm câu hỏi |
| `question`, `answer` | text | Nội dung đầy đủ |

### 9.4. Bảng cột CSV — Exp 2

**Cột cố định:** `idx`, `pdf`, `bloom_level`, `bloom_short`, `sys_bloom_int`, `chapter`

**Với mỗi model đánh giá** (j = 0, 1, 2): `bloom_pred_j`, `bloom_pred_name_j`, `agree_j`, `eval_time_j`

**Cột tổng hợp:** `n_agree`, `is_2llm`, `is_3llm`, `process_time_s`, `question`, `answer`

### 9.5. File phụ (SQLite tạm)

| File | Script | Có thể xóa? |
|------|--------|-------------|
| `experiment/exp1_temp.db` | Exp 1 | Có |
| `experiment/exp2_temp.db` | Exp 2 | Có |
| `experiment/any_pdf_temp.db` | Smoke test | Có |
| `experiment/results/*.csv`, `*.md` | Exp 1, 2 | **Giữ** — dữ liệu thí nghiệm |

### 9.6. Dùng cho luận văn

- Import CSV vào Excel / SPSS / Python pandas
- Trích bảng từ file `*_report_*.md`
- Mô tả phương pháp: trích từ `experiment/exp1.md`, `experiment/exp2.md`

---

## 10. Thời gian & chi phí ước tính

| Tác vụ | Lượt gọi LLM (ước lượng) | Thời gian (ước lượng) |
|--------|--------------------------|------------------------|
| Smoke test | ~1 pipeline | 1–3 phút |
| Exp 1 | ~144 sinh Q&A × 3 model | **2–6 giờ** (tùy PDF & API) |
| Exp 2 | ~120 sinh + ~360 phân loại | **2–4 giờ** |

Script có **delay** giữa PDF/model để tránh rate-limit OpenRouter (`5–10` giây).

**Chi phí OpenRouter:** phụ thuộc model và token. Nên theo dõi dashboard OpenRouter khi chạy lần đầu.

---

## 11. Xử lý lỗi thường gặp

### Không tìm thấy PDF

```
❌ Không tìm thấy PDF nào trong: ...\experiment
```

→ Copy file `.pdf` vào `experiment/` (mục 4).

### Chưa có API key

```
Chưa có API key trong Admin → Cài đặt
```

→ Admin → Cài đặt → dán OpenRouter API key → Lưu → chạy lại.

### Lỗi load app chính / database

```
Không load được app chính — kiểm tra PostgreSQL và instance/bootstrap.json
```

→ Kiểm tra MySQL/XAMPP đang chạy, `bootstrap.json` đúng, đã `python init_db.py`.

### Không trích xuất được nội dung PDF

```
⚠ Không trích xuất được nội dung
```

→ PDF scan ảnh: thử `run_any_pdf.py --ocr` hoặc bật OCR trong Admin.

### Pipeline 0 câu

- PDF quá ngắn hoặc không có cấu trúc chương
- Agent 1 từ chối (nội dung không phù hợp Bloom)
- Hết credit / rate-limit OpenRouter

→ Chạy smoke test với `--bloom 2` hoặc `--bloom 3`, xem log Agent trong terminal.

### `database is locked` (SQLite)

Script đã bật WAL + timeout 60s. Nếu vẫn lỗi:

- Đóng process Python khác đang dùng `exp1_temp.db`
- Xóa file `experiment/exp1_temp.db` / `exp2_temp.db` và chạy lại

### NLTK / punkt

Lần đầu có thể cần internet để tải tokenizer. Nếu lỗi:

```powershell
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

### Rate-limit OpenRouter (429)

- Chờ vài phút
- Tăng delay trong script (biến `DELAY_BETWEEN_PDFS`, `DELAY_BETWEEN_MODELS` đầu file)
- Chạy từng model một (tạm comment model khác trong `MODELS`)

---

## 12. Tóm tắt nhanh

| Chuẩn bị | Lấy ở đâu | Dùng cho |
|----------|-----------|----------|
| 4 PDF giáo trình | Tự tải / sưu tập | Copy vào `experiment/` |
| OpenRouter API key + credit | openrouter.ai → Admin app | Tất cả script |
| App + DB đã init | `install_guide.md` | Đồng bộ cấu hình AI |
| `pip install -r requirements.txt` | Thư mục gốc project | NLTK, pdfplumber, … |

| Chạy script | Đầu ra chính |
|-------------|--------------|
| `run_any_pdf.py` | Terminal only — kiểm tra pipeline |
| `experiment_1_chapter_bleu.py` | `exp1_raw_*.csv` + `exp1_report_*.md` |
| `experiment_2_bloom_accuracy.py` | `exp2_raw_*.csv` + `exp2_report_*.md` |

---

## 13. English summary

**Prerequisites:** Install TEXTQAI ([`install_guide.md`](install_guide.md)), configure **OpenRouter API key** in Admin → Settings, copy **PDF textbooks** into `experiment/`.

**Quick test:**

```bash
python experiment/run_any_pdf.py --pdf path/to/book.pdf
```

**Experiment 1** (BLEU + chapter attribution, 3 models × 4 PDFs):

```bash
python experiment/experiment_1_chapter_bleu.py
```

**Experiment 2** (Bloom label accuracy ACC₂LLM / ACC₃LLM):

```bash
python experiment/experiment_2_bloom_accuracy.py
```

**Outputs:** `experiment/results/exp{1,2}_raw_*.csv` and `*_report_*.md`.

**Methodology:** see [`experiment/exp1.md`](../experiment/exp1.md) and [`experiment/exp2.md`](../experiment/exp2.md).

---

*Tài liệu đi kèm dự án TEXTQAI — cập nhật theo mã nguồn trong `experiment/`.*
