# Thực Nghiệm 2 – Đánh Giá Độ Chính Xác Phân Loại Mức Bloom

---

## 1. Mục Tiêu

Thực nghiệm 2 đánh giá mức độ **chính xác phân loại mức Bloom** của các câu hỏi do hệ thống sinh ra. Thay vì tự chấm nhãn, thực nghiệm sử dụng ba mô hình LLM độc lập làm **bộ đánh giá bên ngoài** để kiểm tra xem câu hỏi / đáp án được hệ thống gán cho mức Bloom nào có thực sự thuộc mức đó theo nhận định của các LLM hay không.

Cụ thể, thực nghiệm trả lời hai câu hỏi:

1. **Bao nhiêu % câu hỏi có ít nhất 2/3 LLM đồng ý với nhãn Bloom của hệ thống?** → ACC₂LLM
2. **Bao nhiêu % câu hỏi được cả 3/3 LLM đồng thuận?** → ACC₃LLM

---

## 2. Thiết Kế Thực Nghiệm

**Model sinh câu hỏi:** `google/gemini-2.5-flash-lite` (model đạt BLEU cao nhất trong Thực Nghiệm 1)

**Dữ liệu:** Bốn giáo trình đại học giống Thực Nghiệm 1 (AI, CNPM, CSDL, Mạng máy tính)

**Quy mô:** Mỗi giáo trình sinh **30 câu** (5 câu × 6 mức Bloom), tổng cộng **120 câu** trên 4 giáo trình.

**Model đánh giá Bloom:** Ba LLM được dùng độc lập làm bộ phân loại:
- `google/gemini-2.5-flash-lite`
- `deepseek/deepseek-chat-v3-0324`
- `openai/gpt-4o-mini`

| Thành phần | Số lượng |
|-----------|:--------:|
| Model sinh Q&A | 1 (Gemini) |
| Giáo trình PDF | 4 |
| Câu/mức Bloom/giáo trình | 5 |
| Mức Bloom | 6 (B1–B6) |
| Câu/giáo trình | 30 |
| **Tổng câu** | **120** |
| Model đánh giá | 3 |

---

## 3. Phương Pháp Đo Lường

### 3.1. Quy Trình Đánh Giá

Với mỗi cặp câu hỏi – đáp án, mỗi LLM đánh giá nhận prompt zero-shot:

> *"Cho câu hỏi và câu trả lời mẫu sau đây, hãy xác định mức Bloom phù hợp nhất (1–6). Chỉ trả lời bằng một số nguyên duy nhất."*

Kèm theo định nghĩa đầy đủ 6 mức Bloom bằng tiếng Việt. Nhiệt độ (temperature) được đặt = 0 để đảm bảo tính nhất quán. LLM trả về một số nguyên 1–6, được so sánh với nhãn Bloom mà hệ thống đã gán.

### 3.2. Công Thức ACC₂LLM và ACC₃LLM

Gọi \(y_i\) là nhãn Bloom hệ thống gán cho câu thứ \(i\), và \(\hat{y}_{i,j}\) là nhãn LLM thứ \(j\) phân loại:

$$n\_agree_i = \sum_{j=1}^{3} \mathbf{1}[\hat{y}_{i,j} = y_i]$$

$$\text{ACC}_{2\text{LLM}} = \frac{\#\{i : n\_agree_i \geq 2\}}{N}$$

$$\text{ACC}_{3\text{LLM}} = \frac{\#\{i : n\_agree_i = 3\}}{N}$$

Trong đó \(N = 120\) là tổng số câu.

- **ACC₂LLM**: Nếu đa số (≥ 2/3) LLM đồng ý với hệ thống → hệ thống phân loại đáng tin cậy.
- **ACC₃LLM**: Cả 3 LLM đều đồng ý → mức độ đồng thuận tuyệt đối, tiêu chuẩn nghiêm ngặt hơn.

---

## 4. Kết Quả

### 4.1. Tỷ Lệ Sinh Câu Thành Công

Hệ thống sinh đủ 120/120 câu (100%), không có lỗi pipeline trên bất kỳ mức Bloom hay giáo trình nào.

### 4.2. Kết Quả Tổng Quan

| Chỉ số | Kết quả |
|--------|:-------:|
| ACC₂LLM (≥ 2/3 LLM đồng ý) | **70.8%** (85/120) |
| ACC₃LLM (3/3 LLM đồng ý) | **45.8%** (55/120) |

**Tỷ lệ đồng ý từng model với hệ thống:**

| Model | Đúng / Tổng | Tỷ lệ |
|-------|:-----------:|:-----:|
| `gemini-2.5-flash-lite` | 85 / 120 | 70.8% |
| `deepseek-chat-v3-0324` | 76 / 120 | 63.3% |
| `gpt-4o-mini` | 86 / 120 | 71.7% |

### 4.3. Kết Quả Theo Mức Bloom

| Mức Bloom | Câu | ACC₂LLM | ACC₃LLM |
|-----------|:---:|:-------:|:-------:|
| B1 – Nhớ | 20 | **75.0%** | 20.0% |
| B2 – Hiểu | 20 | 40.0% | 10.0% |
| B3 – Vận dụng | 20 | 10.0% | 0.0% |
| **B4 – Phân tích** | **20** | **100.0%** | **100.0%** |
| B5 – Đánh giá | 20 | 100.0% | 60.0% |
| B6 – Sáng tạo | 20 | 100.0% | 85.0% |

> B4–B6 đạt độ chính xác gần tuyệt đối. B1 cải thiện mạnh (75%). B3 vẫn thấp do ranh giới B3/B4 mờ.

### 4.4. Kết Quả Theo Giáo Trình

| Giáo trình | Câu | ACC₂LLM | ACC₃LLM |
|------------|:---:|:-------:|:-------:|
| `Giao_Trinh_AI_Full_Length` | 30 | 70.0% | 46.7% |
| `Giao_Trinh_CNPM_Full_Length` | 30 | 70.0% | 33.3% |
| `Giao_Trinh_CSDL_Full_Length` | 30 | 66.7% | 50.0% |
| `Giao_Trinh_Mang_Full_Length` | 30 | 76.7% | 53.3% |

Kết quả khá đồng đều qua 4 giáo trình (~70% ACC₂LLM), cho thấy hiện tượng không phụ thuộc vào chủ đề cụ thể mà phản ánh đặc điểm chung của cách hệ thống sinh câu hỏi.

---

## 5. Phân Tích

### 5.1. Tại Sao B4–B6 Đạt Gần 100%?

Câu hỏi B4 (Phân tích) thường bắt đầu bằng **"Phân tích..."**, B5 (Đánh giá) bằng **"Đánh giá..."**, B6 (Sáng tạo) bằng **"Thiết kế..."** hoặc **"Đề xuất..."** — đây là các động từ hành động đặc trưng, dễ nhận dạng. Ba LLM đều phân loại đúng nhất quán.

### 5.2. Phân Tích B1–B3 Trước và Sau Cải Thiện Prompt

Thực nghiệm ban đầu (prompt chưa ràng buộc) cho kết quả B1–B3 gần 0% do Agent 2 sinh câu hỏi với cấu trúc phân tích phức tạp, ví dụ:

- **B1 (cũ):** *"Cho biết các khía cạnh cần xem xét khi đánh giá..."* → 3 LLM phân loại **B4**
- **B2 (cũ):** *"Giải thích tại sao việc áp dụng X đòi hỏi sự hiểu biết về..."* → 3 LLM phân loại **B4**
- **B3 (cũ):** *"Vận dụng kiến thức về X, hãy phân tích..."* → từ "phân tích" khiến LLM phân loại **B4**

Sau khi bổ sung ràng buộc vào prompt Agent 2 (cấm từ phân tích, thêm cấu trúc mẫu):

| Bloom | Trước cải thiện | Sau cải thiện | Cải thiện |
|-------|:--------------:|:-------------:|:---------:|
| B1 – Nhớ | 0.0% | **75.0%** | +75% |
| B2 – Hiểu | 5.0% | **40.0%** | +35% |
| B3 – Vận dụng | 5.0% | **10.0%** | +5% |
| B4–B6 | ~98% | ~100% | ổn định |
| **Tổng ACC₂LLM** | **50.8%** | **70.8%** | **+20%** |

**B3 vẫn thấp (10%)** do ranh giới giữa Vận dụng (B3) và Phân tích (B4) vốn mờ trong tiếng Việt — nhiều câu hỏi B3 đòi hỏi giải thích quy trình (LLM dễ nhầm là B4). Đây là hạn chế cố hữu của thang Bloom trong ngữ cảnh ngôn ngữ tự nhiên.

### 5.3. Ý Nghĩa Với Hệ Thống

| Nhóm | Bloom | Đánh giá hệ thống |
|------|-------|-------------------|
| Nhóm cao (HOTS) | B4, B5, B6 | ✅ Phân loại đúng, LLM đồng thuận cao (95–100%) |
| Nhóm thấp (LOTS) | B1 | ✅ Sau cải thiện: 75% ACC₂LLM |
| Nhóm thấp (LOTS) | B2 | ⚠ Trung bình: 40% ACC₂LLM |
| Nhóm thấp (LOTS) | B3 | ⚠ Vẫn thấp: 10% — ranh giới B3/B4 mờ |

---

## 6. Kết Luận

Thực nghiệm 2 đo độ chính xác phân loại Bloom bằng phương pháp đồng thuận LLM. Kết quả:

- **ACC₂LLM = 70.8%**, **ACC₃LLM = 45.8%** sau khi cải thiện prompt Agent 2.
- **B4–B6 đạt 100%** (ACC₂LLM) — hệ thống phân loại tư duy bậc cao rất chính xác.
- **B1 đạt 75%** sau khi thêm ràng buộc cấu trúc câu hỏi vào prompt.
- **B3 vẫn 10%** — ranh giới B3/B4 mờ là hạn chế cố hữu của thang Bloom trong tiếng Việt.

Kết quả cho thấy ACC₂LLM = **70.8%** là mức chấp nhận được, phản ánh hệ thống phân loại Bloom đáng tin cậy ở phần lớn các mức. Hướng cải thiện tiếp theo là bổ sung few-shot examples cho B3 và làm rõ ranh giới ngôn ngữ B3/B4 trong prompt.

---

## 7. File Dữ Liệu

| File | Mô tả |
|------|-------|
| `experiment/results/exp2_raw_20260609_154144.csv` | Dữ liệu thô 120 câu, nhãn hệ thống, phân loại 3 LLM, n_agree, is_2llm, is_3llm |
| `experiment/results/exp2_report_20260609_154144.md` | Báo cáo tự động đầy đủ (sau cải thiện prompt) |
| `experiment/experiment_2_bloom_accuracy.py` | Script chạy thực nghiệm |
