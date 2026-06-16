# Thực Nghiệm 1 – Đánh Giá Độ Bám Nguồn Của Câu Hỏi/Đáp Án Sinh Ra So Với Tài Liệu Gốc (BLEU + Attribution)

---

## 1. Mục Tiêu

Thực nghiệm nhằm đánh giá khả năng **bám sát nội dung tài liệu gốc** của các cặp câu hỏi – đáp án được hệ thống tự động sinh ra thông qua pipeline 3 tác nhân AI (Agent 1 – Agent 2 – Agent 3). Cụ thể, thực nghiệm hướng đến hai câu hỏi:

1. **Đáp án có dùng từ ngữ từ tài liệu không?** → đo bằng BLEU-1, BLEU-2, BLEU-4 so với chương nguồn.
2. **Đáp án có bám đúng chương nguồn không?** → đo bằng *Chapter Attribution Accuracy*: tính BLEU-4 giữa đáp án với **tất cả các chương** trong giáo trình, kiểm tra chương nào gần nhất có trùng với chương nguồn hay không.

Ba mô hình ngôn ngữ lớn (LLM) được so sánh để xác định mô hình nào có độ bám nguồn tốt nhất.

---

## 2. Thiết Kế Thực Nghiệm

**Đối tượng so sánh:** Ba mô hình AI được cấu hình làm nhân tố sinh câu hỏi (Agent 2) trong pipeline:

- `google/gemini-2.5-flash-lite`
- `deepseek/deepseek-chat-v3-0324`
- `openai/gpt-4o-mini`

**Dữ liệu đầu vào:** Bốn giáo trình đại học ở định dạng PDF, bao gồm các lĩnh vực Trí tuệ Nhân tạo, Công nghệ Phần mềm, Cơ sở Dữ liệu và Mạng máy tính.

**Quy mô sinh câu:** Với mỗi mô hình, hệ thống sinh **12 câu hỏi/giáo trình** (2 câu × 6 mức Bloom), nhân với 4 giáo trình được **48 câu/model**, tổng cộng **144 câu** cho cả ba mô hình.

| Thành phần | Số lượng |
|-----------|:--------:|
| Mô hình AI | 3 |
| Giáo trình PDF | 4 |
| Câu/mức Bloom/giáo trình | 2 |
| Mức Bloom | 6 (B1–B6) |
| Câu/model | 48 |
| **Tổng câu** | **144** |

---

## 3. Phương Pháp Đo Lường

### 3.1. BLEU (Bilingual Evaluation Understudy)

Thước đo phổ biến trong xử lý ngôn ngữ tự nhiên, đánh giá mức độ trùng khớp n-gram giữa văn bản sinh ra (hypothesis) và văn bản tham chiếu (reference). Thực nghiệm sử dụng đồng thời ba biến thể:

| Chỉ số | Đơn vị đo | Đặc điểm |
|--------|-----------|----------|
| **BLEU-1** | Unigram (từ đơn) | Tỷ lệ từ trong đáp án xuất hiện trong tài liệu gốc; ít nghiêm ngặt nhất |
| **BLEU-2** | Bigram (cụm 2 từ) | Cân bằng giữa độ bao phủ và độ chính xác |
| **BLEU-4** | 4-gram (cụm 4 từ) | Tiêu chuẩn học thuật phổ biến nhất; nghiêm ngặt nhất |

**Công thức tổng quát:**

$$\text{BLEU-N} = BP \times \exp\!\left(\sum_{n=1}^{N} w_n \log p_n\right)$$

Trong đó:
- \(p_n\) = precision của n-gram: tỷ lệ n-gram trong hypothesis xuất hiện trong reference
- \(w_n = \frac{1}{N}\) = trọng số đều cho mỗi bậc n-gram
- \(BP\) = **Brevity Penalty** — hệ số phạt câu quá ngắn:

$$BP = \begin{cases} 1 & \text{nếu } |hyp| \geq |ref| \\ e^{1 - |ref|/|hyp|} & \text{nếu } |hyp| < |ref| \end{cases}$$

BP đảm bảo đáp án quá ngắn (chỉ vài từ trùng) không được điểm cao bất hợp lý.

**Văn bản tham chiếu (reference):** Nội dung chương nguồn tương ứng. Để tránh pha loãng bởi nội dung không liên quan trong một chương dài hàng nghìn từ, hệ thống tự động chọn **top-7 câu có độ tương đồng ngữ nghĩa cao nhất** với đáp án (dựa trên số từ trùng khớp sau khi lọc stopwords tiếng Việt) làm reference.

**Công cụ:** `nltk.translate.bleu_score.sentence_bleu` với `SmoothingFunction.method1`.

### 3.2. Chapter Attribution Accuracy

Với mỗi đáp án sinh ra, hệ thống tính BLEU-4 giữa đáp án đó và **từng chương** trong cùng giáo trình (thường 8 chương), sau đó xác định chương có điểm BLEU-4 cao nhất (`best_bleu_chapter`). Nếu `best_bleu_chapter` trùng với chương nguồn (`source_chapter`) → đáp án **attribution đúng** (`is_correct = True`).

$$\text{Attribution Accuracy} = \frac{\text{Số câu có } best\_bleu\_chapter = source\_chapter}{\text{Tổng số câu}}$$

Chỉ số này cho biết hệ thống có thực sự sinh đáp án từ đúng chương nguồn hay bị lạc sang nội dung chương khác.

---

## 4. Quy Trình Thực Hiện

1. **Trích xuất PDF:** Toàn bộ nội dung văn bản được trích xuất bằng `pdfplumber`, phân tách thành các chương và mục theo cấu trúc tiêu đề.
2. **Xây dựng chapter map:** Pipeline tự động gộp nội dung các mục cùng chương thành `chapter_content_map` — bản đồ đầy đủ nội dung từng chương trong giáo trình.
3. **Sinh câu hỏi – đáp án:** Pipeline 3 tác nhân chạy tuần tự cho từng model và giáo trình. Agent 1 kiểm tra tính khả thi Bloom, Agent 2 sinh Q&A với nội dung mục lẻ làm nguồn chính, Agent 3 đánh giá chất lượng và groundedness.
4. **Tính BLEU và Attribution:** Với mỗi đáp án, tính BLEU-1/2/4 so với chương nguồn; đồng thời tính BLEU-4 so với tất cả chương để tìm `best_bleu_chapter` và `is_correct`.
5. **Tổng hợp:** Kết quả lưu vào CSV (144 dòng × 22 cột, câu hỏi và đáp án đầy đủ) và báo cáo Markdown tự động.

---

## 5. Kết Quả

### 5.1. Tỷ Lệ Sinh Câu Thành Công

| Mô hình | Mục tiêu | Sinh được | Tỷ lệ |
|---------|:--------:|:---------:|:------:|
| `gemini-2.5-flash-lite` | 48 | 48 | 100% |
| `deepseek-chat-v3-0324` | 48 | 48 | 100% |
| `gpt-4o-mini` | 48 | 48 | 100% |
| **Tổng** | **144** | **144** | **100%** |

### 5.2. Điểm BLEU Trung Bình (Đáp Án – Cấp Chương)

| Mô hình | BLEU-1 | BLEU-2 | BLEU-4 |
|---------|:------:|:------:|:------:|
| `gemini-2.5-flash-lite` | **0.2786** | **0.2363** | **0.1903** |
| `gpt-4o-mini` | 0.2605 | 0.2077 | 0.1570 |
| `deepseek-chat-v3-0324` | 0.1740 | 0.1304 | 0.0891 |

### 5.3. BLEU Theo Mức Bloom (3 Model)

| Mức Bloom | Gemini | GPT-4o-mini | DeepSeek |
|-----------|:------:|:-----------:|:--------:|
| B1 – Nhớ | 0.0970 | 0.1027 | 0.0735 |
| B2 – Hiểu | 0.1952 | 0.1814 | 0.0961 |
| B3 – Vận dụng | 0.2806 | 0.1983 | 0.1144 |
| B4 – Phân tích | **0.2950** | 0.1974 | 0.1005 |
| B5 – Đánh giá | 0.1677 | **0.1854** | 0.0868 |
| B6 – Sáng tạo | 0.1062 | 0.0767 | 0.0633 |
| **Trung bình** | **0.1903** | **0.1570** | **0.0891** |

> Bloom 3–4 đạt BLEU cao nhất vì đáp án phân tích phải trích dẫn cụ thể từ tài liệu. Bloom 5–6 thấp hơn do đáp án thiên về tư duy tổng hợp.

### 5.4. Chapter Attribution Accuracy

| Mô hình | Đúng / Tổng | Accuracy |
|---------|:-----------:|:--------:|
| `gpt-4o-mini` | 36 / 48 | **75.0%** |
| `gemini-2.5-flash-lite` | 32 / 48 | 66.7% |
| `deepseek-chat-v3-0324` | 22 / 48 | 45.8% |
| **Tổng** | **90 / 144** | **62.5%** |

**Accuracy theo mức Bloom (3 model):**

| Mức Bloom | Gemini | GPT-4o-mini | DeepSeek |
|-----------|:------:|:-----------:|:--------:|
| B1 – Nhớ | 50.0% | 50.0% | 37.5% |
| B2 – Hiểu | 50.0% | 75.0% | 50.0% |
| B3 – Vận dụng | 50.0% | 50.0% | 12.5% |
| B4 – Phân tích | 75.0% | **100.0%** | 62.5% |
| B5 – Đánh giá | 87.5% | **100.0%** | 62.5% |
| B6 – Sáng tạo | 87.5% | 75.0% | 50.0% |

> GPT-4o-mini đạt attribution accuracy cao nhất (75%), đặc biệt xuất sắc ở B4–B5 (100%). DeepSeek thấp nhất (45.8%), xác nhận xu hướng diễn đạt trừu tượng không bám nguồn.

---

## 6. Giải Thích Ngưỡng Điểm

Trong bài toán **sinh câu hỏi mở từ tài liệu** (Open-ended QA Generation), điểm BLEU không thể kỳ vọng cao như dịch máy vì đáp án diễn đạt tự do, không sao chép nguyên văn:

| Khoảng BLEU-4 | Mức độ | Diễn giải |
|--------------|--------|-----------|
| 0.00 – 0.10 | Rất thấp | Đáp án hầu như không dùng từ ngữ từ tài liệu |
| 0.10 – 0.30 | Thấp | Có một số thuật ngữ và cụm từ từ tài liệu |
| 0.30 – 0.50 | Trung bình | Đáp án bám sát nội dung, dùng nhiều từ ngữ gốc |
| > 0.50 | Khá cao | Đáp án trích dẫn gần như trực tiếp từ tài liệu |

Kết quả thực nghiệm: BLEU-4 trung bình từ **0.089–0.190** → mức *Thấp*, phù hợp với đặc thù bài toán. Gemini B3–B4 đạt BLEU-1 = **0.39–0.41** → tiệm cận *Trung bình*.

**Attribution Accuracy 62.5%** so với baseline ngẫu nhiên 1/8 = **12.5%** → hệ thống sinh đáp án **gấp 5 lần ngẫu nhiên** về khả năng bám đúng chương nguồn.

---

## 7. Kết Luận

Thực nghiệm 1 đánh giá độ bám nguồn của hệ thống qua hai chiều: BLEU (từ ngữ trùng khớp) và Attribution Accuracy (nhận dạng đúng chương nguồn).

- **Gemini 2.5 Flash Lite** dẫn đầu về BLEU (BLEU-4 = 0.190), cho thấy đáp án sử dụng nhiều từ ngữ trực tiếp từ tài liệu nhất.
- **GPT-4o-mini** dẫn đầu về Attribution Accuracy (75.0%), đặc biệt đạt 100% ở B4–B5, cho thấy đáp án bám đúng chương nguồn nhất quán nhất.
- **DeepSeek** thấp nhất cả hai chỉ số, phản ánh xu hướng diễn đạt trừu tượng và tổng quát thay vì bám sát nội dung cụ thể.

Hai chỉ số bổ sung cho nhau: BLEU đo độ trùng từ ngữ, Attribution Accuracy đo khả năng nhận dạng nguồn — tạo thành bộ đánh giá đa chiều, phù hợp cho luận văn.

---

## 8. File Dữ Liệu

| File | Mô tả |
|------|-------|
| `experiment/results/exp1_raw_20260609_085826_excel.csv` | Dữ liệu thô 144 câu, 22 cột, câu hỏi/đáp án đầy đủ, tương thích Excel |
| `experiment/results/exp1_report_20260609_085826.md` | Báo cáo tự động với bảng tổng hợp đầy đủ |
| `experiment/experiment_1_chapter_bleu.py` | Script chạy thực nghiệm |
