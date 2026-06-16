"""
run_experiment.py – Thực nghiệm so sánh 3 model AI trên 4 giáo trình
======================================================================
Chạy: python experiment/run_experiment.py  (từ thư mục gốc dự án)
Hoặc: python run_experiment.py             (từ bên trong thư mục experiment/)

Đầu ra:
  experiment/results/results_raw_<timestamp>.csv
  experiment/results/summary_report_<timestamp>.md
"""

import sys
# Force UTF-8 output trên Windows (tránh UnicodeEncodeError với tiếng Việt)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import os
import time
import csv
import re
import statistics
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ── Path setup ──────────────────────────────────────────────────────────────────
EXPERIMENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT   = EXPERIMENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env ───────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

# ── NLTK download (chỉ lần đầu) ────────────────────────────────────────────────
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("[NLTK] Downloading punkt tokenizer...")
    nltk.download('punkt', quiet=True)

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

# ── Flask app (cần cho DB context của pipeline) ─────────────────────────────────
# Dùng SQLite cho thực nghiệm – không phụ thuộc MySQL server
from flask import Flask
from extensions import db

_sqlite_path = EXPERIMENT_DIR / 'experiment_temp.db'
app = Flask(__name__, template_folder=str(PROJECT_ROOT / 'templates'))
app.config['SECRET_KEY']               = os.getenv('SECRET_KEY', 'experiment-key')
app.config['SQLALCHEMY_DATABASE_URI']  = f'sqlite:///{_sqlite_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ── Cấu hình thực nghiệm ────────────────────────────────────────────────────────
MODELS = [
    'deepseek/deepseek-chat-v3-0324',
    'google/gemini-2.5-flash-lite',
    'openai/gpt-4o-mini',
]

# 4 giáo trình PDF nằm trong thư mục experiment/
PDFS = sorted(EXPERIMENT_DIR.glob('*.pdf'))

# 12 câu hỏi: 2 câu × 6 mức Bloom
BLOOM_CONFIGS = [
    {'bloom_level': 'Bloom 1 (Nhớ)',       'count': 2, 'points': 1.0},
    {'bloom_level': 'Bloom 2 (Hiểu)',      'count': 2, 'points': 1.5},
    {'bloom_level': 'Bloom 3 (Vận dụng)',  'count': 2, 'points': 2.0},
    {'bloom_level': 'Bloom 4 (Phân tích)', 'count': 2, 'points': 2.5},
    {'bloom_level': 'Bloom 5 (Đánh giá)',  'count': 2, 'points': 3.0},
    {'bloom_level': 'Bloom 6 (Sáng tạo)',  'count': 2, 'points': 3.5},
]
TOTAL_QUESTIONS = 12

RESULTS_DIR = EXPERIMENT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

# Delay giữa các lần gọi API (giây) – tránh rate limit
DELAY_BETWEEN_PDFS   = 5
DELAY_BETWEEN_MODELS = 10


# ── Hàm tính BLEU-4 ─────────────────────────────────────────────────────────────
def _select_relevant_sentences(reference: str, hypothesis: str, top_n: int = 3) -> list:
    """
    Chọn top-N câu trong reference có số lượng từ trùng khớp nhiều nhất với hypothesis
    (loại bỏ các từ dừng phổ biến để tránh trùng lặp hư từ).
    """
    hyp_words = set(hypothesis.lower().split())
    # Từ dừng tiếng Việt phổ biến để tránh nhiễu khi tính overlap
    viet_stopwords = {
        'và', 'các', 'của', 'là', 'trong', 'để', 'có', 'một', 'sự', 'như', 'này', 'cho', 'với', 'ra', 'được', 'năm', 'vào'
    }
    hyp_words_filtered = hyp_words - viet_stopwords

    # Tách reference thành câu (dấu chấm, xuống dòng)
    sentences = re.split(r'(?<=[.!?\n])\s+', reference)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 10]

    # Gán điểm overlap cho mỗi câu
    scored = []
    for sent in sentences:
        words = sent.lower().split()
        if not words:
            continue
        words_set = set(words) - viet_stopwords
        # Số lượng từ trùng khớp thực tế
        overlap = len(words_set & hyp_words_filtered)
        scored.append((overlap, words))

    # Sắp xếp theo số lượng từ trùng khớp giảm dần
    scored.sort(key=lambda x: x[0], reverse=True)
    selected_tokens = []
    for _, words in scored[:top_n]:
        selected_tokens.extend(words)

    return selected_tokens if selected_tokens else reference.lower().split()[:100]


def compute_bleu4(hypothesis: str, reference: str) -> float:
    """
    Tính BLEU-4 (cumulative 4-gram BLEU) giữa:
      hypothesis = đáp án sinh ra bởi AI
      reference  = nội dung section gốc trong giáo trình

    Dùng top-3 relevant sentences làm reference để BLEU có ý nghĩa
    khi reference >> hypothesis. Dùng SmoothingFunction().method1
    để tránh BLEU = 0 khi 4-gram không khớp hoàn toàn.
    """
    hyp_tokens = hypothesis.lower().split()

    if not hyp_tokens or not reference.strip():
        return 0.0

    # Chọn top-3 câu liên quan nhất làm reference
    ref_tokens = _select_relevant_sentences(reference, hypothesis, top_n=3)

    if len(ref_tokens) < 4:
        return 0.0

    smoother = SmoothingFunction().method1
    score = sentence_bleu(
        references=[ref_tokens],
        hypothesis=hyp_tokens,
        weights=(0.25, 0.25, 0.25, 0.25),   # BLEU-4 tiêu chuẩn
        smoothing_function=smoother,
    )
    return round(float(score), 4)


# ── Hàm rút gọn tên Bloom ───────────────────────────────────────────────────────
def short_bloom(bl: str) -> str:
    """'Bloom 3 (Vận dụng)' → 'B3'"""
    m = re.search(r'Bloom\s*(\d)', bl)
    return f"B{m.group(1)}" if m else bl


# ── Hàm chạy thực nghiệm ────────────────────────────────────────────────────────
def run_all():
    import config as _cfg
    from services.pdf import extract_pdf_text_plain
    from services.pipeline import run_agent_pipeline

    if not PDFS:
        print(f"❌ Không tìm thấy file PDF nào trong: {EXPERIMENT_DIR}")
        return

    print(f"\n{'='*70}")
    print(f"  THỰC NGHIỆM SO SÁNH 3 MODEL AI – BLEU-4")
    print(f"{'='*70}")
    print(f"  Models  : {len(MODELS)}")
    print(f"  PDFs    : {len(PDFS)}")
    print(f"  Câu/PDF : {TOTAL_QUESTIONS}")
    print(f"  Tổng    : {len(MODELS) * len(PDFS) * TOTAL_QUESTIONS} câu")
    print(f"{'='*70}\n")

    all_rows = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    with app.app_context():
        # Tạo tất cả bảng trong SQLite (chạy lần đầu)
        import models as _models  # noqa: ensure all models are registered
        db.create_all()
        print(f"  [DB] SQLite ready: {_sqlite_path}")

        for model_idx, model_name in enumerate(MODELS, 1):
            # ── Override model config tại runtime ──────────────────────────────
            _cfg.QUESTION_MODEL        = model_name
            _cfg.ANSWER_MODEL          = model_name
            _cfg.ANSWER_FALLBACK_MODEL = model_name

            model_short = model_name.split('/')[-1]
            print(f"\n{'─'*70}")
            print(f"  [{model_idx}/{len(MODELS)}] MODEL: {model_name}")
            print(f"{'─'*70}")

            for pdf_idx, pdf_path in enumerate(PDFS, 1):
                pdf_stem = pdf_path.stem
                print(f"\n  [{pdf_idx}/{len(PDFS)}] PDF: {pdf_stem}")
                print(f"  {'─'*50}")

                # ── Trích xuất text PDF ─────────────────────────────────────
                try:
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    content, extraction_stats = extract_pdf_text_plain(pdf_bytes)
                except Exception as e:
                    print(f"  ❌ Lỗi đọc PDF: {e}")
                    continue

                if not content.strip():
                    print(f"  ⚠ Không trích xuất được text từ {pdf_path.name}")
                    continue

                print(f"  ✓ Đã đọc PDF: {len(content):,} ký tự")

                # ── Chạy pipeline ───────────────────────────────────────────
                # Reset session để tránh lỗi cascade từ lần chạy trước
                db.session.rollback()
                t_start = time.time()
                try:
                    results = run_agent_pipeline(
                        content          = content,
                        extraction_stats = extraction_stats,
                        bloom_configs    = BLOOM_CONFIGS,
                        question_count   = TOTAL_QUESTIONS,
                        algo_type        = None,
                        user_id          = None,
                        document_id      = None,
                        use_ocr          = False,
                        progress_callback= None,
                    )
                except Exception as e:
                    print(f"  ❌ Pipeline lỗi: {e}")
                    import traceback; traceback.print_exc()
                    continue

                t_total = round(time.time() - t_start, 2)
                print(f"\n  ✅ Pipeline xong: {len(results)}/{TOTAL_QUESTIONS} câu | {t_total}s tổng")

                # ── Tính BLEU-4 cho từng câu ────────────────────────────────
                for r in results:
                    section_content = r.get('section_content', '')
                    answer          = r.get('answer', '')

                    bleu4 = compute_bleu4(answer, section_content) if section_content else 0.0

                    row = {
                        'model':           model_name,
                        'model_short':     model_short,
                        'pdf':             pdf_stem,
                        'bloom_level':     r.get('bloom_level', ''),
                        'bloom_short':     short_bloom(r.get('bloom_level', '')),
                        'question':        r.get('question', '').replace('\n', ' '),
                        'answer_preview':  answer[:200].replace('\n', ' '),
                        'answer':          answer.replace('\n', ' '),
                        'section_content': section_content.replace('\n', ' '),
                        'section_info':    r.get('section_info', ''),
                        'process_time_s':  r.get('process_time', 0),
                        'bleu4':           bleu4,
                        'answer_len':      len(answer.split()),
                        'ref_len':         len(section_content.split()),
                        'total_points':    r.get('total_points', 0),
                    }
                    all_rows.append(row)

                    print(f"  {row['bloom_short']:3s} | BLEU-4={bleu4:.4f} | "
                          f"t={r.get('process_time',0):.1f}s | "
                          f"'{r.get('section_info','')[:40]}'")

                # Delay giữa PDF
                if pdf_idx < len(PDFS):
                    print(f"\n  ⏳ Chờ {DELAY_BETWEEN_PDFS}s trước PDF tiếp theo...")
                    time.sleep(DELAY_BETWEEN_PDFS)

            # Delay giữa model
            if model_idx < len(MODELS):
                print(f"\n  ⏳ Chờ {DELAY_BETWEEN_MODELS}s trước model tiếp theo...")
                time.sleep(DELAY_BETWEEN_MODELS)

    # ── Xuất CSV ─────────────────────────────────────────────────────────────────
    if not all_rows:
        print("\n❌ Không có kết quả nào để lưu!")
        return

    csv_path = RESULTS_DIR / f'results_raw_{timestamp}.csv'
    fieldnames = list(all_rows[0].keys())
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n✅ CSV đã lưu: {csv_path}")

    # ── Sinh báo cáo Markdown ────────────────────────────────────────────────────
    report_path = generate_report(all_rows, timestamp)
    print(f"✅ Báo cáo: {report_path}")
    print("\n" + "="*70)
    print("  THỰC NGHIỆM HOÀN THÀNH!")
    print("="*70)


# ── Hàm sinh báo cáo Markdown ───────────────────────────────────────────────────
def generate_report(rows: list, timestamp: str) -> Path:
    """Tạo file báo cáo tổng kết kết quả thực nghiệm."""

    by_model  = defaultdict(list)
    by_bloom  = defaultdict(list)
    for r in rows:
        by_model[r['model']].append(r)
        by_bloom[r['bloom_short']].append(r)

    bloom_order = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6']
    bloom_names = {
        'B1': 'Bloom 1 – Nhớ',
        'B2': 'Bloom 2 – Hiểu',
        'B3': 'Bloom 3 – Vận dụng',
        'B4': 'Bloom 4 – Phân tích',
        'B5': 'Bloom 5 – Đánh giá',
        'B6': 'Bloom 6 – Sáng tạo',
    }
    pdf_list = sorted(set(r['pdf'] for r in rows))

    def mean_bleu(subset):
        vals = [r['bleu4'] for r in subset]
        return statistics.mean(vals) if vals else 0.0

    def mean_time(subset):
        vals = [r['process_time_s'] for r in subset]
        return statistics.mean(vals) if vals else 0.0

    def fmt(v):
        return f"{v:.4f}"

    lines = []

    # ── Tiêu đề ─────────────────────────────────────────────────────────────────
    lines += [
        "# Báo Cáo Thực Nghiệm – Hệ Thống Sinh Câu Hỏi Theo Thang Bloom",
        "",
        f"> Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
        "## Thông Tin Thực Nghiệm",
        "",
        f"| Tham số | Giá trị |",
        f"|---------|---------|",
        f"| Số mô hình so sánh | {len(MODELS)} |",
        f"| Số giáo trình PDF | {len(PDFS)} |",
        f"| Số câu hỏi / giáo trình | {TOTAL_QUESTIONS} (2 câu × 6 mức Bloom) |",
        f"| Tổng câu hỏi sinh | {len(rows)} |",
        f"| Chỉ số đánh giá chính | BLEU-4 (cumulative 4-gram) |",
        "",
    ]

    # ── Bảng 1: Tổng hợp theo Model ─────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Bảng 1. Kết Quả Tổng Hợp Theo Mô Hình",
        "",
        "| Mô hình | Câu sinh được | BLEU-4 TB | Thời gian TB (s/câu) |",
        "|---------|:-------------:|:---------:|:--------------------:|",
    ]
    for model in MODELS:
        m_rows = by_model.get(model, [])
        short  = model.split('/')[-1]
        n      = len(m_rows)
        b4     = mean_bleu(m_rows)
        t_avg  = mean_time(m_rows)
        lines.append(f"| `{short}` | {n} | **{fmt(b4)}** | {t_avg:.2f} |")
    lines.append("")

    # ── Bảng 2: BLEU-4 theo Mức Bloom × Model ───────────────────────────────────
    lines += [
        "---",
        "",
        "## Bảng 2. BLEU-4 Theo Mức Bloom và Mô Hình",
        "",
    ]
    model_shorts = [m.split('/')[-1] for m in MODELS]
    header = "| Mức Bloom | " + " | ".join(f"`{s}`" for s in model_shorts) + " |"
    sep    = "|-----------|" + "|".join([":-------:"]*len(MODELS)) + "|"
    lines += [header, sep]
    for bk in bloom_order:
        row_vals = []
        for model in MODELS:
            subset = [r for r in by_model.get(model, []) if r['bloom_short'] == bk]
            row_vals.append(fmt(mean_bleu(subset)) if subset else "–")
        lines.append(f"| {bloom_names.get(bk, bk)} | " + " | ".join(row_vals) + " |")
    lines.append("")

    # ── Bảng 3: BLEU-4 theo Giáo Trình × Model ──────────────────────────────────
    lines += [
        "---",
        "",
        "## Bảng 3. BLEU-4 Theo Giáo Trình và Mô Hình",
        "",
    ]
    header3 = "| Giáo trình | " + " | ".join(f"`{s}`" for s in model_shorts) + " |"
    sep3    = "|------------|" + "|".join([":-------:"]*len(MODELS)) + "|"
    lines += [header3, sep3]
    for pdf in pdf_list:
        row_vals = []
        for model in MODELS:
            subset = [r for r in by_model.get(model, []) if r['pdf'] == pdf]
            row_vals.append(fmt(mean_bleu(subset)) if subset else "–")
        lines.append(f"| `{pdf}` | " + " | ".join(row_vals) + " |")
    lines.append("")

    # ── Bảng 4: Thời gian xử lý theo Model × Giáo Trình ────────────────────────
    lines += [
        "---",
        "",
        "## Bảng 4. Thời Gian Xử Lý Trung Bình (giây/câu)",
        "",
        header3.replace("BLEU-4", "Thời gian (s)"),
        sep3,
    ]
    lines[-2] = "| Giáo trình | " + " | ".join(f"`{s}`" for s in model_shorts) + " |"
    for pdf in pdf_list:
        row_vals = []
        for model in MODELS:
            subset = [r for r in by_model.get(model, []) if r['pdf'] == pdf]
            row_vals.append(f"{mean_time(subset):.2f}" if subset else "–")
        lines.append(f"| `{pdf}` | " + " | ".join(row_vals) + " |")
    lines.append("")

    # ── Nhận xét ─────────────────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Nhận Xét",
        "",
        "### Về BLEU-4",
        "",
        "- **BLEU-4** (Bilingual Evaluation Understudy – 4-gram) đo độ trùng khớp "
        "4-gram liên tiếp giữa đáp án sinh ra và nội dung section gốc của giáo trình.",
        "- Thang điểm: 0.0 (không trùng) → 1.0 (trùng hoàn toàn).",
        "- Mức Bloom thấp (B1–B2 – Nhớ/Hiểu) thường có BLEU-4 **cao hơn** vì "
        "đáp án trích dẫn trực tiếp từ tài liệu nguồn.",
        "- Mức Bloom cao (B5–B6 – Đánh giá/Sáng tạo) có BLEU-4 **thấp hơn** là "
        "bình thường, vì đòi hỏi tư duy phân tích/sáng tạo dựa trên nguồn.",
        "",
        "### Về Thời Gian Xử Lý",
        "",
        "- Thời gian đo từ lúc Agent 2 bắt đầu sinh đến khi Agent 3 chấp nhận.",
        "- Bao gồm thời gian retry nếu Agent 3 từ chối và yêu cầu sinh lại.",
        "",
    ]

    report_path = RESULTS_DIR / f'summary_report_{timestamp}.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return report_path


# ── Entry point ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    run_all()
