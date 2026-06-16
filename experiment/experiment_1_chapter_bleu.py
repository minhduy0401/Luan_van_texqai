"""
experiment_1_chapter_bleu.py
====================================================
Thực Nghiệm 1 – Kiểm tra BLEU câu hỏi / đáp án sinh ra
so với nội dung chương (chapter) trong tài liệu gốc

Mục tiêu:
  • Sinh 48 câu/model × 3 model = 144 câu tổng
    (4 giáo trình × 12 câu/giáo trình × 3 model)
  • Tính BLEU-4 cho từng câu (đáp án so với nội dung chương)
  • So sánh model nào cho BLEU bám nguồn tốt nhất

Chạy từ thư mục gốc:
    python experiment/experiment_1_chapter_bleu.py

Chạy từ thư mục experiment/:
    python experiment_1_chapter_bleu.py

Đầu ra:
    experiment/results/exp1_raw_<timestamp>.csv
    experiment/results/exp1_report_<timestamp>.md
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import re
import csv
import time
import statistics
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ── Path setup ──────────────────────────────────────────────────────────────────
EXPERIMENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT   = EXPERIMENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── NLTK ────────────────────────────────────────────────────────────────────────
import nltk
for _res in ('tokenizers/punkt', 'tokenizers/punkt_tab'):
    try:
        nltk.data.find(_res)
    except LookupError:
        nltk.download(_res.split('/')[-1], quiet=True)

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

# ── Flask app – dùng SQLite để không phụ thuộc MySQL ────────────────────────────
from flask import Flask
from extensions import db

_sqlite_path = EXPERIMENT_DIR / 'exp1_temp.db'
app = Flask(__name__, template_folder=str(PROJECT_ROOT / 'templates'))
app.config['SECRET_KEY']               = 'exp1-key'
# WAL mode + timeout 60s để tránh "database is locked" khi pipeline ghi log nhanh
app.config['SQLALCHEMY_DATABASE_URI']  = f'sqlite:///{_sqlite_path}?timeout=60'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 60, 'check_same_thread': False},
    'pool_pre_ping': True,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def _enable_wal_mode(db_app):
    """Bật WAL journal mode cho SQLite – cho phép đọc/ghi đồng thời."""
    with db_app.app_context():
        from sqlalchemy import text
        try:
            db.session.execute(text('PRAGMA journal_mode=WAL'))
            db.session.execute(text('PRAGMA busy_timeout=60000'))
            db.session.commit()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  CẤU HÌNH THỰC NGHIỆM
# ══════════════════════════════════════════════════════════════════════════════

# 3 model AI cần so sánh
MODELS = [
    'google/gemini-2.5-flash-lite',
    'deepseek/deepseek-chat-v3-0324',
    'openai/gpt-4o-mini',
]

# 4 giáo trình PDF – nằm trong thư mục experiment/
PDFS = sorted(EXPERIMENT_DIR.glob('*.pdf'))

# 12 câu/giáo trình = 2 câu × 6 mức Bloom
BLOOM_CONFIGS = [
    {'bloom_level': 'Bloom 1 (Nhớ)',       'count': 2, 'points': 1.0},
    {'bloom_level': 'Bloom 2 (Hiểu)',      'count': 2, 'points': 1.5},
    {'bloom_level': 'Bloom 3 (Vận dụng)',  'count': 2, 'points': 2.0},
    {'bloom_level': 'Bloom 4 (Phân tích)', 'count': 2, 'points': 2.5},
    {'bloom_level': 'Bloom 5 (Đánh giá)',  'count': 2, 'points': 3.0},
    {'bloom_level': 'Bloom 6 (Sáng tạo)',  'count': 2, 'points': 3.5},
]
QUESTIONS_PER_PDF = 12          # 2 × 6
QUESTIONS_PER_MODEL = QUESTIONS_PER_PDF * len(PDFS)   # 12 × 4 = 48
TARGET_TOTAL = QUESTIONS_PER_MODEL * len(MODELS)       # 48 × 3 = 144

RESULTS_DIR = EXPERIMENT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

DELAY_BETWEEN_PDFS   = 5    # giây – tránh rate-limit
DELAY_BETWEEN_MODELS = 10   # giây

# Stopwords tiếng Việt dùng khi lọc tương đồng cho BLEU
_VIET_STOPWORDS = {
    'và', 'các', 'của', 'là', 'trong', 'để', 'có', 'một', 'sự', 'như',
    'này', 'cho', 'với', 'ra', 'được', 'năm', 'vào', 'từ', 'theo', 'khi',
    'đã', 'sẽ', 'đang', 'không', 'về', 'tại', 'hay', 'hoặc', 'thì',
    'nên', 'mà', 'do', 'bởi', 'vì', 'sau', 'trước', 'nếu', 'giữa',
}


# ══════════════════════════════════════════════════════════════════════════════
#  HÀM TÍNH BLEU (1 / 2 / 4)
# ══════════════════════════════════════════════════════════════════════════════

def _top_relevant_sentences(reference: str, hypothesis: str, top_n: int) -> list:
    """
    Trả về token list từ top-N câu trong reference có số từ trùng nhiều nhất
    với hypothesis (sau khi lọc stopwords). Giúp BLEU có ý nghĩa hơn khi
    reference dài (toàn chương có thể hàng nghìn từ).
    """
    hyp_words = set(hypothesis.lower().split()) - _VIET_STOPWORDS
    sentences = re.split(r'(?<=[.!?\n])\s+', reference)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 10]

    scored = []
    for sent in sentences:
        words_set = set(sent.lower().split()) - _VIET_STOPWORDS
        overlap   = len(words_set & hyp_words)
        scored.append((overlap, sent.lower().split()))

    scored.sort(key=lambda x: x[0], reverse=True)
    tokens = []
    for _, words in scored[:top_n]:
        tokens.extend(words)

    # Fallback: lấy 200 từ đầu reference nếu không chọn được gì
    return tokens if tokens else reference.lower().split()[:200]


def _compute_bleu_n(hypothesis: str, ref_tokens: list, n: int) -> float:
    """
    Tính BLEU-n tổng quát (n = 1, 2 hoặc 4) với uniform weights.
    Dùng SmoothingFunction.method1 để tránh điểm 0 khi n-gram ngắn.
    """
    hyp_tokens = hypothesis.lower().split()
    if not hyp_tokens or len(ref_tokens) < n:
        return 0.0
    w = 1.0 / n
    weights = tuple([w] * n)
    score = sentence_bleu(
        references=[ref_tokens],
        hypothesis=hyp_tokens,
        weights=weights,
        smoothing_function=SmoothingFunction().method1,
    )
    return round(float(score), 4)


def compute_bleu_chapter(hypothesis: str, chapter_text: str, n: int = 4) -> float:
    """
    BLEU-n giữa hypothesis và nội dung chương nguồn.
    Chọn top-7 câu liên quan nhất làm reference.
    """
    if not hypothesis.strip() or not chapter_text.strip():
        return 0.0
    ref_tokens = _top_relevant_sentences(chapter_text, hypothesis, top_n=7)
    return _compute_bleu_n(hypothesis, ref_tokens, n)


def compute_bleu_section(hypothesis: str, section_text: str, n: int = 4) -> float:
    """
    BLEU-n so với nội dung mục (section).
    Chọn top-3 câu liên quan nhất làm reference.
    """
    if not hypothesis.strip() or not section_text.strip():
        return 0.0
    ref_tokens = _top_relevant_sentences(section_text, hypothesis, top_n=3)
    return _compute_bleu_n(hypothesis, ref_tokens, n)


# Giữ alias cũ để không phá vỡ code còn sót
def compute_bleu4_chapter(hypothesis: str, chapter_text: str) -> float:
    return compute_bleu_chapter(hypothesis, chapter_text, n=4)


def compute_bleu4_section(hypothesis: str, section_text: str) -> float:
    return compute_bleu_section(hypothesis, section_text, n=4)


def short_bloom(bl: str) -> str:
    """'Bloom 3 (Vận dụng)' → 'B3'"""
    m = re.search(r'Bloom\s*(\d)', bl)
    return f"B{m.group(1)}" if m else bl


# ══════════════════════════════════════════════════════════════════════════════
#  CHẠY THỰC NGHIỆM
# ══════════════════════════════════════════════════════════════════════════════

def run_all():
    import config as _cfg
    from services.pdf import extract_pdf_text_plain
    from services.pipeline import run_agent_pipeline

    if not PDFS:
        print(f"❌ Không tìm thấy PDF nào trong: {EXPERIMENT_DIR}")
        return

    print(f"\n{'='*72}")
    print(f"  THỰC NGHIỆM 1 – BLEU CÂU HỎI / ĐÁP ÁN SO VỚI NỘI DUNG CHƯƠNG")
    print(f"{'='*72}")
    print(f"  Model AI     : {len(MODELS)} model")
    for m in MODELS:
        print(f"                 • {m}")
    print(f"  Giáo trình   : {len(PDFS)} PDF")
    for p in PDFS:
        print(f"                 • {p.stem}")
    print(f"  Câu/model    : {len(PDFS)} GT × {QUESTIONS_PER_PDF} câu = {QUESTIONS_PER_MODEL} câu")
    print(f"  Tổng mục tiêu: {len(MODELS)} model × {QUESTIONS_PER_MODEL} = {TARGET_TOTAL} câu")
    print(f"  Reference    : nội dung CHƯƠNG (chapter) tương ứng trong giáo trình")
    print(f"{'='*72}\n")

    all_rows  = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Bộ đếm tiến độ tổng
    total_generated = 0
    total_attempted = 0

    with app.app_context():
        import models as _models  # noqa – đảm bảo các model ORM được đăng ký
        db.create_all()
        _enable_wal_mode(app)
        print(f"  [DB] SQLite (WAL mode): {_sqlite_path}\n")

        for model_idx, model_name in enumerate(MODELS, 1):
            # Override model tại runtime – pipeline đọc _cfg.QUESTION_MODEL
            _cfg.QUESTION_MODEL        = model_name
            _cfg.ANSWER_MODEL          = model_name
            _cfg.ANSWER_FALLBACK_MODEL = model_name

            model_short = model_name.split('/')[-1]
            model_generated = 0

            print(f"\n{'─'*72}")
            print(f"  [{model_idx}/{len(MODELS)}] MODEL: {model_name}")
            print(f"{'─'*72}")

            for pdf_idx, pdf_path in enumerate(PDFS, 1):
                pdf_stem = pdf_path.stem
                print(f"\n  [{pdf_idx}/{len(PDFS)}] Giáo trình: {pdf_stem}")
                print(f"  {'─'*60}")

                # Reset session trước mỗi PDF để tránh lỗi PendingRollback lan sang lần sau
                try:
                    db.session.rollback()
                except Exception:
                    pass

                # ── Đọc PDF ─────────────────────────────────────────────────
                try:
                    content, extraction_stats = extract_pdf_text_plain(
                        pdf_path.read_bytes()
                    )
                except Exception as e:
                    print(f"  ❌ Lỗi đọc PDF: {e}")
                    total_attempted += QUESTIONS_PER_PDF
                    continue

                if not content.strip():
                    print(f"  ⚠ Không trích xuất được nội dung")
                    total_attempted += QUESTIONS_PER_PDF
                    continue

                print(f"  ✓ Đọc PDF xong: {len(content):,} ký tự")

                # ── Chạy pipeline ────────────────────────────────────────────
                db.session.rollback()
                chapter_map = {}   # sẽ được cập nhật bởi pipeline qua _chapter_map_out
                t_start = time.time()
                try:
                    pipeline_results = run_agent_pipeline(
                        content           = content,
                        extraction_stats  = extraction_stats,
                        bloom_configs     = BLOOM_CONFIGS,
                        question_count    = QUESTIONS_PER_PDF,
                        algo_type         = None,
                        user_id           = None,
                        document_id       = None,
                        use_ocr           = False,
                        progress_callback = None,
                        _chapter_map_out  = chapter_map,
                    )
                except Exception as e:
                    print(f"  ❌ Pipeline lỗi: {e}")
                    import traceback; traceback.print_exc()
                    total_attempted += QUESTIONS_PER_PDF
                    continue

                elapsed = round(time.time() - t_start, 1)
                generated = len(pipeline_results)
                total_attempted  += QUESTIONS_PER_PDF
                total_generated  += generated
                model_generated  += generated

                print(
                    f"\n  ✅ Pipeline xong: {generated}/{QUESTIONS_PER_PDF} câu "
                    f"| {elapsed}s tổng "
                    f"| {elapsed/max(generated,1):.1f}s/câu\n"
                )

                # ── Tính BLEU cho từng câu ───────────────────────────────────
                for r in pipeline_results:
                    question        = r.get('question', '')
                    answer          = r.get('answer', '')
                    section_content = r.get('section_content', '')
                    chapter_key     = r.get('chapter_key', 'N/A')
                    bloom_level     = r.get('bloom_level', '')

                    # BLEU đáp án vs chương nguồn (chỉ số chính: B1, B2, B4)
                    src_content    = chapter_map.get(chapter_key, section_content)
                    bleu1_ans_src  = compute_bleu_chapter(answer, src_content, n=1)
                    bleu2_ans_src  = compute_bleu_chapter(answer, src_content, n=2)
                    bleu4_ans_src  = compute_bleu_chapter(answer, src_content, n=4)

                    # BLEU đáp án vs từng chapter → tìm chapter gần nhất
                    chap_scores = {}
                    for ck, cc in chapter_map.items():
                        chap_scores[ck] = compute_bleu_chapter(answer, cc, n=4)

                    best_chapter = max(chap_scores, key=chap_scores.get) if chap_scores else chapter_key
                    best_bleu    = chap_scores.get(best_chapter, 0.0)
                    is_correct   = (best_chapter == chapter_key)

                    # BLEU đáp án vs section (đối chiếu)
                    bleu4_ans_sec = compute_bleu_section(answer, section_content, n=4)

                    # BLEU câu hỏi vs chương nguồn (phụ)
                    bleu4_q_src   = compute_bleu_chapter(question, src_content, n=4)

                    row = {
                        # ─ định danh ─────────────────────────────────────────
                        'model':              model_name,
                        'model_short':        model_short,
                        'pdf':                pdf_stem,
                        'bloom_level':        bloom_level,
                        'bloom_short':        short_bloom(bloom_level),
                        'source_chapter':     chapter_key,
                        'section_info':       r.get('section_info', ''),
                        # ─ BLEU đáp án vs chương nguồn (chỉ số chính) ────────
                        'bleu1_ans_chapter':  bleu1_ans_src,
                        'bleu2_ans_chapter':  bleu2_ans_src,
                        'bleu4_ans_chapter':  bleu4_ans_src,
                        # ─ Chapter attribution ────────────────────────────────
                        'best_bleu_chapter':  best_chapter,
                        'best_bleu_score':    best_bleu,
                        'is_correct':         is_correct,
                        # ─ BLEU vs section (đối chiếu) ───────────────────────
                        'bleu4_ans_section':  bleu4_ans_sec,
                        # ─ BLEU câu hỏi (phụ) ───────────────────────────────
                        'bleu4_q_chapter':    bleu4_q_src,
                        # ─ độ dài ────────────────────────────────────────────
                        'answer_words':       len(answer.split()),
                        'question_words':     len(question.split()),
                        'chapter_words':      len(src_content.split()),
                        'section_words':      len(section_content.split()),
                        # ─ thời gian / điểm ─────────────────────────────────
                        'process_time_s':     r.get('process_time', 0),
                        'total_points':       r.get('total_points', 0),
                        # ─ nội dung ĐẦY ĐỦ ──────────────────────────────────
                        'question':           question.replace('\n', ' | '),
                        'answer':             answer.replace('\n', ' | '),
                    }
                    all_rows.append(row)

                    correct_mark = '✅' if is_correct else f'❌→{best_chapter}'
                    print(
                        f"  {row['bloom_short']:3s} | "
                        f"BLEU-1={bleu1_ans_src:.4f} "
                        f"BLEU-2={bleu2_ans_src:.4f} "
                        f"BLEU-4={bleu4_ans_src:.4f} | "
                        f"src={chapter_key[:12]} best={best_chapter[:12]} {correct_mark}"
                    )

                if pdf_idx < len(PDFS):
                    print(f"\n  ⏳ Chờ {DELAY_BETWEEN_PDFS}s...")
                    time.sleep(DELAY_BETWEEN_PDFS)

            # Tổng kết mỗi model
            print(f"\n  📊 [{model_short}] Tổng sinh được: "
                  f"{model_generated}/{QUESTIONS_PER_MODEL} câu "
                  f"({model_generated/QUESTIONS_PER_MODEL*100:.0f}%)")

            if model_idx < len(MODELS):
                print(f"  ⏳ Chờ {DELAY_BETWEEN_MODELS}s trước model tiếp theo...")
                time.sleep(DELAY_BETWEEN_MODELS)

    # ── Tổng kết toàn bộ ─────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"  KẾT QUẢ TỔNG: {total_generated}/{TARGET_TOTAL} câu "
          f"({total_generated/TARGET_TOTAL*100:.1f}%)")
    print(f"{'='*72}")

    if not all_rows:
        print("❌ Không có kết quả nào để lưu!")
        return

    # ── Xuất CSV ─────────────────────────────────────────────────────────────
    csv_path = RESULTS_DIR / f'exp1_raw_{timestamp}.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(all_rows[0].keys()),
            quoting=csv.QUOTE_ALL,   # buộc Excel đọc mọi ô là text, tránh #NAME?
        )
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n✅ CSV: {csv_path}")

    report_path = _generate_report(all_rows, timestamp, total_generated, total_attempted)
    print(f"✅ Báo cáo: {report_path}")
    print(f"\n{'='*72}\n  THỰC NGHIỆM 1 HOÀN THÀNH!\n{'='*72}")


# ══════════════════════════════════════════════════════════════════════════════
#  SINH BÁO CÁO MARKDOWN
# ══════════════════════════════════════════════════════════════════════════════

def _generate_report(rows: list, timestamp: str,
                     total_generated: int, total_attempted: int) -> Path:
    """Tạo báo cáo Markdown cho Thực Nghiệm 1.
    Cấu trúc: lần lượt từng model (theo thứ tự MODELS), từng Bloom B1→B6.
    """

    # ── Nhóm dữ liệu ─────────────────────────────────────────────────────────
    by_model   = defaultdict(list)
    by_chapter = defaultdict(list)   # key = (pdf, source_chapter)

    for r in rows:
        by_model[r['model']].append(r)
        by_chapter[(r['pdf'], r['source_chapter'])].append(r)

    bloom_order = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6']
    bloom_names = {
        'B1': 'Bloom 1 (Nhớ)',       'B2': 'Bloom 2 (Hiểu)',
        'B3': 'Bloom 3 (Vận dụng)',  'B4': 'Bloom 4 (Phân tích)',
        'B5': 'Bloom 5 (Đánh giá)',  'B6': 'Bloom 6 (Sáng tạo)',
    }
    pdf_list = sorted(set(r['pdf'] for r in rows))

    def _mean(lst):  return statistics.mean(lst) if lst else 0.0
    def fmt(v):      return f"{v:.4f}"
    def pct(n, d):   return f"{n/d*100:.1f}%" if d else "–"

    def mean_f(subset, field):
        vals = [r[field] for r in subset
                if isinstance(r.get(field), (int, float))]
        return _mean(vals)

    lines = []

    # ══════════════════════════════════════════════════════════════════════════
    # TIÊU ĐỀ VÀ THÔNG TIN THỰC NGHIỆM
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "# Thực Nghiệm 1 – BLEU Câu Hỏi / Đáp Án So Với Nội Dung Chương",
        "",
        f"> Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
        "## 1. Thông Tin Thực Nghiệm",
        "",
        "| Tham số | Giá trị |",
        "|---------|---------|",
        f"| Số mô hình AI | {len(MODELS)} |",
        f"| Số giáo trình PDF | {len(PDFS)} |",
        f"| Câu mục tiêu / giáo trình | {QUESTIONS_PER_PDF} (2 câu × 6 mức Bloom) |",
        f"| Câu mục tiêu / model | {QUESTIONS_PER_MODEL} (= {QUESTIONS_PER_PDF} × {len(PDFS)} GT) |",
        f"| Tổng câu mục tiêu | **{TARGET_TOTAL}** (= {QUESTIONS_PER_MODEL} × {len(MODELS)} model) |",
        f"| Tổng câu sinh được | **{total_generated}** / {TARGET_TOTAL} ({pct(total_generated, TARGET_TOTAL)}) |",
        "",
        "**Chỉ số đánh giá:**",
        "",
        "| Ký hiệu | Ý nghĩa |",
        "|---------|---------|",
        "| **BLEU-1-chap** | BLEU-1 (unigram) đáp án so với nội dung *chương nguồn* |",
        "| **BLEU-2-chap** | BLEU-2 (bigram) đáp án so với nội dung *chương nguồn* |",
        "| **BLEU-4-chap** | BLEU-4 (4-gram) đáp án so với nội dung *chương nguồn* |",
        "| **BLEU-4-sec**  | BLEU-4 đáp án so với nội dung *mục lẻ* nguồn (đối chiếu) |",
        "| **best_bleu_chapter** | Chương có BLEU-4 cao nhất khi so với toàn bộ chương trong giáo trình |",
        "| **is_correct** | True nếu chương gần nhất = chương nguồn (attribution đúng) |",
        "| **Accuracy** | % câu có is_correct = True trên tổng số câu |",
        "",
        "> BLEU-n: đo độ trùng khớp n-gram liên tiếp giữa đáp án sinh ra và tài liệu gốc, thang 0.0→1.0.",
        "> Reference = top-7 câu liên quan nhất trong chương; dùng SmoothingFunction.method1.",
        "> BLEU-1 (unigram) ≥ BLEU-2 (bigram) ≥ BLEU-4 (4-gram) do yêu cầu độ khớp tăng dần.",
        "",
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # BẢNG 1: TỶ LỆ SINH CÂU THÀNH CÔNG
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "---",
        "",
        "## 2. Tỷ Lệ Sinh Câu Thành Công",
        "",
        "| Mô hình | Mục tiêu | Sinh được | Tỷ lệ |",
        "|---------|:--------:|:---------:|:------:|",
    ]
    for model in MODELS:
        short = model.split('/')[-1]
        n     = len(by_model.get(model, []))
        lines.append(f"| `{short}` | {QUESTIONS_PER_MODEL} | {n} | {pct(n, QUESTIONS_PER_MODEL)} |")
    lines += [
        f"| **Tổng** | {TARGET_TOTAL} | **{total_generated}** | {pct(total_generated, TARGET_TOTAL)} |",
        "",
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # BẢNG 2: KẾT QUẢ BLEU — LẦN LƯỢT TỪNG MODEL, TỪNG BLOOM B1→B6
    # Cấu trúc: mỗi model là 1 section, mỗi Bloom là 1 dòng trong bảng
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "---",
        "",
        "## 3. Kết Quả BLEU Theo Từng Model – Từng Mức Bloom",
        "",
    ]

    for model in MODELS:
        short  = model.split('/')[-1]
        m_rows = by_model.get(model, [])
        n_model = len(m_rows)

        # Tính BLEU tổng của model này
        avg_b1c = mean_f(m_rows, 'bleu1_ans_chapter')
        avg_b2c = mean_f(m_rows, 'bleu2_ans_chapter')
        avg_b4c = mean_f(m_rows, 'bleu4_ans_chapter')
        avg_b4s = mean_f(m_rows, 'bleu4_ans_section')
        avg_t   = mean_f(m_rows, 'process_time_s')

        lines += [
            f"### 3.{MODELS.index(model)+1}. Model: `{short}`",
            "",
            f"Câu sinh được: **{n_model}** / {QUESTIONS_PER_MODEL} "
            f"({pct(n_model, QUESTIONS_PER_MODEL)}) | "
            f"Thời gian trung bình: **{avg_t:.2f}s/câu**",
            "",
            "| Mức Bloom | Câu | BLEU-1-chap | BLEU-2-chap | BLEU-4-chap | BLEU-4-sec | t̄ (s) |",
            "|-----------|:---:|:-----------:|:-----------:|:-----------:|:----------:|:-----:|",
        ]

        for bk in bloom_order:
            bname  = bloom_names[bk]
            subset = [r for r in m_rows if r['bloom_short'] == bk]
            n_b    = len(subset)
            if subset:
                b1c = mean_f(subset, 'bleu1_ans_chapter')
                b2c = mean_f(subset, 'bleu2_ans_chapter')
                b4c = mean_f(subset, 'bleu4_ans_chapter')
                b4s = mean_f(subset, 'bleu4_ans_section')
                t   = mean_f(subset, 'process_time_s')
                lines.append(
                    f"| {bname} | {n_b} | {fmt(b1c)} | {fmt(b2c)} | {fmt(b4c)}"
                    f" | {fmt(b4s)} | {t:.2f} |"
                )
            else:
                lines.append(f"| {bname} | 0 | – | – | – | – | – |")

        # Dòng tổng của model
        lines += [
            f"| **Tổng / TB** | **{n_model}** | **{fmt(avg_b1c)}** | **{fmt(avg_b2c)}** | **{fmt(avg_b4c)}**"
            f" | {fmt(avg_b4s)} | {avg_t:.2f} |",
            "",
        ]

        # ─ Bảng phụ: BLEU theo giáo trình (trong cùng section của model) ─
        lines += [
            f"**BLEU theo giáo trình (model `{short}`):**",
            "",
            "| Giáo trình | Câu | BLEU-1-chap | BLEU-2-chap | BLEU-4-chap | t̄ (s) |",
            "|------------|:---:|:-----------:|:-----------:|:-----------:|:-----:|",
        ]
        for pdf in pdf_list:
            subset = [r for r in m_rows if r['pdf'] == pdf]
            n_p    = len(subset)
            if subset:
                b1c = mean_f(subset, 'bleu1_ans_chapter')
                b2c = mean_f(subset, 'bleu2_ans_chapter')
                b4c = mean_f(subset, 'bleu4_ans_chapter')
                t   = mean_f(subset, 'process_time_s')
                lines.append(f"| `{pdf}` | {n_p} | {fmt(b1c)} | {fmt(b2c)} | {fmt(b4c)} | {t:.2f} |")
            else:
                lines.append(f"| `{pdf}` | 0 | – | – | – | – |")
        lines.append("")

    # ══════════════════════════════════════════════════════════════════════════
    # BẢNG 3: SO SÁNH NGANG 3 MODEL – THEO TỪNG BLOOM (3 mức BLEU)
    # ══════════════════════════════════════════════════════════════════════════
    model_shorts = [m.split('/')[-1] for m in MODELS]

    lines += [
        "---",
        "",
        "## 4. So Sánh BLEU Đáp Án (Cấp Chương): 3 Model × 6 Mức Bloom",
        "",
        "*(Đọc theo hàng: so sánh 3 model tại cùng mức Bloom)*",
        "*(Đọc theo cột: theo dõi xu hướng BLEU từ B1→B6 của 1 model)*",
        "",
    ]

    for bleu_n, field in [(1, 'bleu1_ans_chapter'), (2, 'bleu2_ans_chapter'), (4, 'bleu4_ans_chapter')]:
        sep    = f"|-----------|" + "|".join([":-------:"] * len(MODELS)) + "|"
        header = f"| Mức Bloom | " + " | ".join(f"`{s}`" for s in model_shorts) + " |"
        lines += [
            f"### BLEU-{bleu_n} Đáp Án – Cấp Chương",
            "",
            header, sep,
        ]
        for bk in bloom_order:
            bname    = bloom_names[bk]
            row_vals = []
            for model in MODELS:
                subset = [r for r in by_model.get(model, []) if r['bloom_short'] == bk]
                row_vals.append(fmt(mean_f(subset, field)) if subset else "–")
            lines.append(f"| {bname} | " + " | ".join(row_vals) + " |")

        total_vals = [fmt(mean_f(by_model.get(m, []), field)) for m in MODELS]
        lines += [
            f"| **Trung bình** | " + " | ".join(f"**{v}**" for v in total_vals) + " |",
            "",
        ]

    # ══════════════════════════════════════════════════════════════════════════
    # BẢNG 4: CHAPTER ATTRIBUTION ACCURACY
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "---",
        "",
        "## 5. Chapter Attribution Accuracy",
        "",
        "> **Attribution accuracy**: tỷ lệ câu mà chương có BLEU-4 cao nhất (trong toàn giáo trình)",
        "> trùng với chương nguồn sinh ra câu hỏi đó.",
        "> Accuracy cao → hệ thống sinh đáp án thực sự bám vào đúng chương nguồn.",
        "",
    ]

    # Bảng tổng hợp accuracy theo model
    lines += [
        "### 5.1. Accuracy Theo Model",
        "",
        "| Model | Đúng | Tổng | Accuracy |",
        "|-------|:----:|:----:|:--------:|",
    ]
    for model in MODELS:
        short   = model.split('/')[-1]
        m_rows  = by_model.get(model, [])
        correct = sum(1 for r in m_rows if r.get('is_correct') is True)
        total   = len(m_rows)
        lines.append(f"| `{short}` | {correct} | {total} | {pct(correct, total)} |")
    all_correct = sum(1 for r in rows if r.get('is_correct') is True)
    lines += [
        f"| **Tổng** | {all_correct} | {len(rows)} | **{pct(all_correct, len(rows))}** |",
        "",
    ]

    # Bảng accuracy theo model × Bloom
    sep_attr    = "|-----------|" + "|".join([":-------:"] * len(MODELS)) + "|"
    header_attr = "| Mức Bloom | " + " | ".join(f"`{m.split('/')[-1]}`" for m in MODELS) + " |"
    lines += [
        "### 5.2. Accuracy Theo Model × Mức Bloom",
        "",
        header_attr, sep_attr,
    ]
    for bk in bloom_order:
        bname    = bloom_names[bk]
        row_vals = []
        for model in MODELS:
            subset  = [r for r in by_model.get(model, []) if r['bloom_short'] == bk]
            correct = sum(1 for r in subset if r.get('is_correct') is True)
            row_vals.append(pct(correct, len(subset)) if subset else "–")
        lines.append(f"| {bname} | " + " | ".join(row_vals) + " |")
    lines.append("")

    # Chi tiết từng câu sai attribution
    wrong_rows = [r for r in rows if r.get('is_correct') is False]
    if wrong_rows:
        lines += [
            "### 5.3. Các Câu Attribution Sai",
            "",
            "| Model | PDF | Bloom | Chương Nguồn | Chương Best BLEU | BLEU-4 Best |",
            "|-------|-----|-------|:------------:|:----------------:|:-----------:|",
        ]
        for r in wrong_rows:
            lines.append(
                f"| `{r['model_short']}` | `{r['pdf'][:20]}` | {r['bloom_short']}"
                f" | {r['source_chapter']} | **{r['best_bleu_chapter']}** | {fmt(r['best_bleu_score'])} |"
            )
        lines.append("")

    # ══════════════════════════════════════════════════════════════════════════
    # BẢNG 5: BLEU THEO TỪNG CHƯƠNG (GỘP 3 MODEL)
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "---",
        "",
        "## 6. BLEU Đáp Án Theo Từng Chương (Gộp 3 Model)",
        "",
        "| Giáo trình | Chương Nguồn | Câu | BLEU-1-chap | BLEU-2-chap | BLEU-4-chap | Accuracy |",
        "|------------|--------------|:---:|:-----------:|:-----------:|:-----------:|:--------:|",
    ]
    for pdf in pdf_list:
        chapter_keys = sorted(
            set(r['source_chapter'] for r in rows if r['pdf'] == pdf),
            key=lambda c: (
                int(re.search(r'\d+', c).group())
                if re.search(r'\d+', c) else 999
            ),
        )
        for ck in chapter_keys:
            subset  = [r for r in rows if r['pdf'] == pdf and r['source_chapter'] == ck]
            n       = len(subset)
            b1c     = mean_f(subset, 'bleu1_ans_chapter')
            b2c     = mean_f(subset, 'bleu2_ans_chapter')
            b4c     = mean_f(subset, 'bleu4_ans_chapter')
            correct = sum(1 for r in subset if r.get('is_correct') is True)
            lines.append(
                f"| `{pdf}` | {ck} | {n} | {fmt(b1c)} | {fmt(b2c)} | {fmt(b4c)} | {pct(correct, n)} |"
            )
    lines.append("")

    # ══════════════════════════════════════════════════════════════════════════
    # GHI CHÚ
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "---",
        "",
        "## 7. Ghi Chú",
        "",
        "- **BLEU-1** (unigram): tỷ lệ từ đơn trong đáp án xuất hiện trong tài liệu gốc.",
        "- **BLEU-2** (bigram): cụm 2 từ liên tiếp trùng khớp.",
        "- **BLEU-4** (4-gram): tiêu chuẩn học thuật, nghiêm ngặt nhất.",
        "- **Attribution accuracy**: % câu hỏi mà đáp án sinh ra gần chương nguồn nhất (trong toàn giáo trình).",
        "- Accuracy < 100% → đáp án bị ảnh hưởng bởi nội dung chương khác hoặc kiến thức ngoài tài liệu.",
        "- Bloom 5–6 (Đánh giá/Sáng tạo) thường có BLEU thấp hơn và accuracy thấp hơn — đặc thù bài toán.",
        "- Dòng '–' = pipeline không sinh được câu nào cho mức Bloom đó.",
        "",
    ]

    report_path = RESULTS_DIR / f'exp1_report_{timestamp}.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return report_path


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    run_all()
