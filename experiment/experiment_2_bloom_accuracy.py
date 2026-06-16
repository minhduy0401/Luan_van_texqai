"""
experiment_2_bloom_accuracy.py
====================================================
Thực Nghiệm 2 – Đánh Giá Độ Chính Xác Phân Loại Mức Bloom

Thiết kế:
  1. Sinh 30 câu hỏi / đáp án (5 câu × 6 mức Bloom) từ 1 giáo trình
     bằng model Gemini 2.5 Flash Lite (model tốt nhất về BLEU từ Thực Nghiệm 1)
  2. Gửi từng cặp Q&A cho 3 LLM (Gemini, DeepSeek, GPT-4o-mini)
     để phân loại mức Bloom (1–6)
  3. So sánh nhãn LLM trả về với nhãn mức Bloom hệ thống đã gán
  4. Tính:
       ACC_2LLM = tỷ lệ câu có ≥ 2/3 LLM đồng ý với hệ thống
       ACC_3LLM = tỷ lệ câu có cả 3/3 LLM đồng ý với hệ thống

Chạy từ thư mục gốc:
    python experiment/experiment_2_bloom_accuracy.py

Đầu ra:
    experiment/results/exp2_raw_<timestamp>.csv
    experiment/results/exp2_report_<timestamp>.md
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
from datetime import datetime
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────────────────
EXPERIMENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT   = EXPERIMENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

from openai import OpenAI

# ── Flask app – SQLite (chỉ dùng cho pipeline, không lưu dữ liệu thật) ───────
from flask import Flask
from extensions import db

_sqlite_path = EXPERIMENT_DIR / 'exp2_temp.db'
app = Flask(__name__, template_folder=str(PROJECT_ROOT / 'templates'))
app.config['SECRET_KEY']               = os.getenv('SECRET_KEY', 'exp2-key')
app.config['SQLALCHEMY_DATABASE_URI']  = f'sqlite:///{_sqlite_path}?timeout=60'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 60, 'check_same_thread': False},
    'pool_pre_ping': True,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def _enable_wal_mode(db_app):
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

# Model sinh Q&A (Agent 2)
GENERATOR_MODEL = 'google/gemini-2.5-flash-lite'

# 3 model AI đánh giá mức Bloom
EVALUATOR_MODELS = [
    'google/gemini-2.5-flash-lite',
    'deepseek/deepseek-chat-v3-0324',
    'openai/gpt-4o-mini',
]

# 4 giáo trình PDF – giống Thực Nghiệm 1
PDFS = sorted(EXPERIMENT_DIR.glob('*.pdf'))
if not PDFS:
    raise FileNotFoundError(f"Không tìm thấy PDF trong: {EXPERIMENT_DIR}")

# 30 câu/giáo trình = 5 câu × 6 mức Bloom
BLOOM_CONFIGS = [
    {'bloom_level': 'Bloom 1 (Nhớ)',       'count': 5, 'points': 1.0},
    {'bloom_level': 'Bloom 2 (Hiểu)',      'count': 5, 'points': 1.5},
    {'bloom_level': 'Bloom 3 (Vận dụng)',  'count': 5, 'points': 2.0},
    {'bloom_level': 'Bloom 4 (Phân tích)', 'count': 5, 'points': 2.5},
    {'bloom_level': 'Bloom 5 (Đánh giá)',  'count': 5, 'points': 3.0},
    {'bloom_level': 'Bloom 6 (Sáng tạo)',  'count': 5, 'points': 3.5},
]
QUESTIONS_PER_PDF = 30   # 5 × 6
QUESTIONS_TARGET  = QUESTIONS_PER_PDF * len(PDFS)   # 30 × 4 = 120

RESULTS_DIR = EXPERIMENT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

DELAY_BETWEEN_EVALS = 1   # giây – tránh rate-limit khi gọi LLM đánh giá
DELAY_BETWEEN_ROWS  = 2   # giây giữa mỗi hàng (3 lần gọi LLM)

# Nhãn Bloom chuẩn
BLOOM_LABELS = {
    1: 'Bloom 1 (Nhớ)',
    2: 'Bloom 2 (Hiểu)',
    3: 'Bloom 3 (Vận dụng)',
    4: 'Bloom 4 (Phân tích)',
    5: 'Bloom 5 (Đánh giá)',
    6: 'Bloom 6 (Sáng tạo)',
}

BLOOM_NAMES_SHORT = {
    'B1': 'Nhớ', 'B2': 'Hiểu', 'B3': 'Vận dụng',
    'B4': 'Phân tích', 'B5': 'Đánh giá', 'B6': 'Sáng tạo',
}


# ══════════════════════════════════════════════════════════════════════════════
#  GỌI LLM ĐỂ PHÂN LOẠI BLOOM
# ══════════════════════════════════════════════════════════════════════════════

_OPENROUTER_CLIENT = None

def _get_client() -> OpenAI:
    global _OPENROUTER_CLIENT
    if _OPENROUTER_CLIENT is None:
        api_key = os.getenv('OPENROUTER_API_KEY', '')
        if not api_key:
            raise EnvironmentError('OPENROUTER_API_KEY không được thiết lập trong .env')
        _OPENROUTER_CLIENT = OpenAI(
            api_key=api_key,
            base_url='https://openrouter.ai/api/v1',
        )
    return _OPENROUTER_CLIENT


_BLOOM_EVAL_PROMPT = """\
Bạn là chuyên gia giáo dục chuyên đánh giá câu hỏi theo thang Bloom. \
Cho câu hỏi và câu trả lời mẫu dưới đây, hãy xác định mức Bloom phù hợp nhất.

Câu hỏi: {question}

Câu trả lời: {answer}

Các mức Bloom (chọn 1 số duy nhất):
1 - Nhớ (Remember): Nhắc lại, liệt kê, định nghĩa, nhận biết thông tin đã học
2 - Hiểu (Understand): Giải thích, mô tả, tóm tắt, diễn giải khái niệm
3 - Vận dụng (Apply): Áp dụng kiến thức giải quyết vấn đề cụ thể
4 - Phân tích (Analyze): Phân tích thành phần, so sánh, phân loại, lập luận chi tiết
5 - Đánh giá (Evaluate): Đánh giá, phán xét, phê phán dựa trên tiêu chí rõ ràng
6 - Sáng tạo (Create): Thiết kế, đề xuất, tổng hợp tạo ra giải pháp hoặc sản phẩm mới

Chỉ trả lời bằng một số nguyên duy nhất từ 1 đến 6, không giải thích thêm."""


def classify_bloom(question: str, answer: str, model: str, retries: int = 3) -> int | None:
    """
    Gọi LLM để phân loại mức Bloom của cặp Q&A.
    Trả về số nguyên 1–6, hoặc None nếu thất bại.
    """
    client  = _get_client()
    content = _BLOOM_EVAL_PROMPT.format(
        question=question[:800],
        answer=answer[:1000],
    )
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': content}],
                max_tokens=10,
                temperature=0,
            )
            raw = resp.choices[0].message.content.strip()
            # Lấy số đầu tiên trong chuỗi trả về
            m = re.search(r'[1-6]', raw)
            if m:
                return int(m.group())
        except Exception as e:
            print(f"    ⚠ classify_bloom [{model}] lần {attempt+1}: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


def bloom_to_int(bloom_str: str) -> int | None:
    """'Bloom 3 (Vận dụng)' → 3"""
    m = re.search(r'Bloom\s*(\d)', bloom_str)
    return int(m.group(1)) if m else None


def short_bloom(bl: str) -> str:
    """'Bloom 3 (Vận dụng)' → 'B3'"""
    m = re.search(r'Bloom\s*(\d)', bl)
    return f"B{m.group(1)}" if m else bl


# ══════════════════════════════════════════════════════════════════════════════
#  SINH BÁO CÁO
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_pct(n: int, d: int) -> str:
    return f'{n/d*100:.1f}%' if d else '–'


def _generate_report(rows: list, timestamp: str) -> str:
    """Tạo báo cáo Markdown từ danh sách rows."""
    n_total = len(rows)
    n_correct_2 = sum(1 for r in rows if r['is_2llm'])
    n_correct_3 = sum(1 for r in rows if r['is_3llm'])

    bloom_order = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6']
    bloom_names = {
        'B1': 'Bloom 1 (Nhớ)', 'B2': 'Bloom 2 (Hiểu)',
        'B3': 'Bloom 3 (Vận dụng)', 'B4': 'Bloom 4 (Phân tích)',
        'B5': 'Bloom 5 (Đánh giá)', 'B6': 'Bloom 6 (Sáng tạo)',
    }
    eval_shorts = [m.split('/')[-1] for m in EVALUATOR_MODELS]

    lines = [
        f'# Thực Nghiệm 2 – Đánh Giá Độ Chính Xác Phân Loại Mức Bloom',
        f'',
        f'> Thời gian: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}',
        f'',
        f'## 1. Thông Tin Thực Nghiệm',
        f'',
        f'| Tham số | Giá trị |',
        f'|---------|---------|',
        f'| Model sinh Q&A | `{GENERATOR_MODEL.split("/")[-1]}` |',
        f'| Giáo trình | {len(PDFS)} PDF ({", ".join(p.stem[:20] for p in PDFS)}) |',
        f'| Câu hỏi mục tiêu | {QUESTIONS_TARGET} (5 câu × 6 mức Bloom × 4 giáo trình) |',
        f'| Câu hỏi sinh được | **{n_total}** / {QUESTIONS_TARGET} ({_fmt_pct(n_total, QUESTIONS_TARGET)}) |',
        f'| Model đánh giá Bloom | {len(EVALUATOR_MODELS)} model |',
        f'',
        f'**Model đánh giá:**',
        f'',
    ]
    for m in EVALUATOR_MODELS:
        lines.append(f'- `{m.split("/")[-1]}`')

    lines += [
        f'',
        f'**Chỉ số đánh giá:**',
        f'',
        f'| Ký hiệu | Ý nghĩa |',
        f'|---------|---------|',
        f'| **ACC₂LLM** | Tỷ lệ câu có ≥ 2/3 LLM đồng ý với nhãn Bloom của hệ thống |',
        f'| **ACC₃LLM** | Tỷ lệ câu có cả 3/3 LLM đồng ý với nhãn Bloom của hệ thống |',
        f'| **n_agree** | Số LLM (0–3) đồng ý với hệ thống cho từng câu |',
        f'',
        f'> Đồng ý = LLM phân loại đúng mức Bloom như hệ thống đã gán.',
        f'> ACC₂LLM ≥ ACC₃LLM do điều kiện 2/3 dễ thoả hơn 3/3.',
        f'',
        f'---',
        f'',
        f'## 2. Kết Quả Tổng Quan',
        f'',
        f'| Chỉ số | Giá trị |',
        f'|--------|---------|',
        f'| Tổng câu đánh giá | {n_total} |',
        f'| Câu có ≥ 2/3 LLM đồng ý (ACC₂LLM) | **{n_correct_2}** / {n_total} ({_fmt_pct(n_correct_2, n_total)}) |',
        f'| Câu có 3/3 LLM đồng ý (ACC₃LLM) | **{n_correct_3}** / {n_total} ({_fmt_pct(n_correct_3, n_total)}) |',
        f'',
    ]

    # Per-model agreement rate
    lines += [
        f'**Tỷ lệ đồng ý từng model với hệ thống:**',
        f'',
        f'| Model | Đúng | Tổng | Tỷ lệ |',
        f'|-------|:----:|:----:|:-----:|',
    ]
    for i, m_short in enumerate(eval_shorts):
        col = f'agree_{i}'
        n_agree = sum(1 for r in rows if r.get(col))
        lines.append(f'| `{m_short}` | {n_agree} | {n_total} | {_fmt_pct(n_agree, n_total)} |')

    lines += ['', '---', '', '## 3. Kết Quả Theo Mức Bloom', '']

    # ACC per Bloom level
    lines += [
        f'| Mức Bloom | Câu | n_agree=3 | n_agree=2 | n_agree=1 | n_agree=0 | ACC₂LLM | ACC₃LLM |',
        f'|-----------|:---:|:---------:|:---------:|:---------:|:---------:|:-------:|:-------:|',
    ]
    for bk in bloom_order:
        subset = [r for r in rows if r['bloom_short'] == bk]
        n = len(subset)
        if n == 0:
            lines.append(f'| {bloom_names[bk]} | 0 | – | – | – | – | – | – |')
            continue
        c3  = sum(1 for r in subset if r['n_agree'] == 3)
        c2  = sum(1 for r in subset if r['n_agree'] == 2)
        c1  = sum(1 for r in subset if r['n_agree'] == 1)
        c0  = sum(1 for r in subset if r['n_agree'] == 0)
        a2  = sum(1 for r in subset if r['is_2llm'])
        a3  = sum(1 for r in subset if r['is_3llm'])
        lines.append(
            f'| {bloom_names[bk]} | {n} | {c3} | {c2} | {c1} | {c0} '
            f'| {_fmt_pct(a2, n)} | {_fmt_pct(a3, n)} |'
        )
    lines += ['']

    # Per-model agreement per Bloom
    lines += [
        f'**Tỷ lệ đồng ý từng model theo mức Bloom:**',
        f'',
        f'| Mức Bloom | `{eval_shorts[0]}` | `{eval_shorts[1]}` | `{eval_shorts[2]}` |',
        f'|-----------|:-------:|:-------:|:-------:|',
    ]
    for bk in bloom_order:
        subset = [r for r in rows if r['bloom_short'] == bk]
        n = len(subset)
        if n == 0:
            lines.append(f'| {bloom_names[bk]} | – | – | – |')
            continue
        vals = []
        for i in range(len(EVALUATOR_MODELS)):
            col = f'agree_{i}'
            n_ag = sum(1 for r in subset if r.get(col))
            vals.append(_fmt_pct(n_ag, n))
        lines.append(f'| {bloom_names[bk]} | {vals[0]} | {vals[1]} | {vals[2]} |')
    lines += ['', '---', '', '## 3b. Kết Quả Theo Giáo Trình', '']

    pdf_names = sorted(set(r.get('pdf', '') for r in rows))
    lines += [
        f'| Giáo trình | Câu | ACC₂LLM | ACC₃LLM |',
        f'|------------|:---:|:-------:|:-------:|',
    ]
    for pn in pdf_names:
        subset = [r for r in rows if r.get('pdf') == pn]
        n = len(subset)
        a2 = sum(1 for r in subset if r['is_2llm'])
        a3 = sum(1 for r in subset if r['is_3llm'])
        lines.append(f'| `{pn[:30]}` | {n} | {_fmt_pct(a2, n)} | {_fmt_pct(a3, n)} |')

    lines += ['', '---', '']

    # Bảng chi tiết từng câu
    lines += [
        f'## 4. Chi Tiết Từng Câu',
        f'',
        f'| # | PDF | Bloom | Câu hỏi (rút gọn) | {eval_shorts[0]} | {eval_shorts[1]} | {eval_shorts[2]} | n_agree | ACC₂ | ACC₃ |',
        f'|---|-----|-------|-------------------|:---:|:---:|:---:|:---:|:---:|:---:|',
    ]
    for i, r in enumerate(rows, 1):
        q_short = r['question'][:55].replace('|', '/')
        if len(r['question']) > 55:
            q_short += '…'
        sys_bloom = r['bloom_short']
        pdf_short = r.get('pdf', '')[:18]
        vals = []
        for j in range(len(EVALUATOR_MODELS)):
            pred = r.get(f'bloom_pred_{j}')
            agree = r.get(f'agree_{j}')
            if pred is None:
                vals.append('?')
            else:
                tick = '✅' if agree else '❌'
                vals.append(f'B{pred} {tick}')
        a2 = '✅' if r['is_2llm'] else '❌'
        a3 = '✅' if r['is_3llm'] else '❌'
        lines.append(
            f'| {i} | {pdf_short} | {sys_bloom} | {q_short} | {vals[0]} | {vals[1]} | {vals[2]} '
            f'| {r["n_agree"]} | {a2} | {a3} |'
        )

    lines += [
        f'',
        f'---',
        f'',
        f'## 5. Ghi Chú',
        f'',
        f'- **ACC₂LLM**: Nếu ≥ 2 trong 3 LLM phân loại đúng mức Bloom → hệ thống đáng tin cậy.',
        f'- **ACC₃LLM**: Cả 3 LLM đều đồng ý → mức độ đồng thuận cao nhất.',
        f'- Model đánh giá dùng prompt zero-shot, temperature=0 để đảm bảo tính nhất quán.',
        f'- Bloom 1–3 có thể bị phân loại nhầm lên B4 nếu câu hỏi dùng cấu trúc phân tích phức tạp.',
        f'- Kết quả lưu đầy đủ tại: `experiment/results/exp2_raw_{timestamp}.csv`',
    ]

    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  CHẠY THỰC NGHIỆM
# ══════════════════════════════════════════════════════════════════════════════

def _eval_qa_list(pipeline_results: list, pdf_stem: str, all_rows: list):
    """Đánh giá Bloom cho danh sách Q&A đã sinh từ 1 PDF."""
    eval_shorts = [m.split('/')[-1] for m in EVALUATOR_MODELS]
    n_gen       = len(pipeline_results)
    global_idx  = len(all_rows) + 1

    print(f"\n  {'─'*72}")
    print(f"  🔍 Đánh giá Bloom {n_gen} câu bằng {len(EVALUATOR_MODELS)} model...\n")

    for local_idx, r in enumerate(pipeline_results, 1):
        question    = r.get('question', '')
        answer      = r.get('answer', '')
        bloom_level = r.get('bloom_level', '')
        chapter_key = r.get('chapter_key', 'N/A')
        sys_bloom   = bloom_to_int(bloom_level)
        bk          = short_bloom(bloom_level)

        print(f"  [{global_idx:03d}] {bk} | {question[:60]}…")

        row = {
            'idx':            global_idx,
            'pdf':            pdf_stem,
            'bloom_level':    bloom_level,
            'bloom_short':    bk,
            'sys_bloom_int':  sys_bloom,
            'chapter':        chapter_key,
            'process_time_s': r.get('process_time', 0),
            'question':       question.replace('\n', ' | '),
            'answer':         answer.replace('\n', ' | '),
        }

        agrees = []
        for j, eval_model in enumerate(EVALUATOR_MODELS):
            m_short = eval_shorts[j]
            t0      = time.time()
            pred    = classify_bloom(question, answer, eval_model)
            t_eval  = round(time.time() - t0, 1)
            agree   = (pred == sys_bloom) if pred is not None else False

            row[f'bloom_pred_{j}']      = pred
            row[f'bloom_pred_name_{j}'] = BLOOM_LABELS.get(pred, '?') if pred else '?'
            row[f'agree_{j}']           = agree
            row[f'eval_time_{j}']       = t_eval
            agrees.append(agree)

            mark = '✅' if agree else f'❌(pred=B{pred})'
            print(f"       {m_short:35s} → B{pred if pred else "?"} {mark} [{t_eval}s]")

            if j < len(EVALUATOR_MODELS) - 1:
                time.sleep(DELAY_BETWEEN_EVALS)

        n_agree         = sum(agrees)
        row['n_agree']  = n_agree
        row['is_2llm']  = n_agree >= 2
        row['is_3llm']  = n_agree == 3
        all_rows.append(row)

        print(f"       → n_agree={n_agree}  ACC₂={'✅' if row['is_2llm'] else '❌'}  ACC₃={'✅' if row['is_3llm'] else '❌'}\n")

        if local_idx < n_gen:
            time.sleep(DELAY_BETWEEN_ROWS)

        global_idx += 1


def run_all():
    import config as _cfg
    from services.pdf import extract_pdf_text_plain
    from services.pipeline import run_agent_pipeline

    print(f"\n{'='*72}")
    print(f"  THỰC NGHIỆM 2 – ĐỘ CHÍNH XÁC PHÂN LOẠI MỨC BLOOM")
    print(f"{'='*72}")
    print(f"  Model sinh Q&A : {GENERATOR_MODEL}")
    print(f"  Giáo trình     : {len(PDFS)} PDF")
    for p in PDFS:
        print(f"                   • {p.stem}")
    print(f"  Câu/giáo trình : {QUESTIONS_PER_PDF} (5 câu × 6 mức Bloom)")
    print(f"  Tổng mục tiêu  : {QUESTIONS_TARGET} câu")
    print(f"  Model đánh giá : {len(EVALUATOR_MODELS)} model")
    for m in EVALUATOR_MODELS:
        print(f"                   • {m}")
    print(f"{'='*72}\n")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    all_rows  = []

    with app.app_context():
        import models as _models  # noqa
        db.create_all()
        _enable_wal_mode(app)

        # Override config để dùng generator model
        _cfg.QUESTION_MODEL        = GENERATOR_MODEL
        _cfg.ANSWER_MODEL          = GENERATOR_MODEL
        _cfg.ANSWER_FALLBACK_MODEL = GENERATOR_MODEL

        for pdf_idx, pdf_path in enumerate(PDFS, 1):
            pdf_stem = pdf_path.stem
            print(f"\n{'─'*72}")
            print(f"  [{pdf_idx}/{len(PDFS)}] Giáo trình: {pdf_stem}")
            print(f"{'─'*72}")

            try:
                db.session.rollback()
            except Exception:
                pass

            # ── Đọc PDF ──────────────────────────────────────────────────
            print(f"  📄 Đọc PDF...")
            try:
                content, extraction_stats = extract_pdf_text_plain(
                    pdf_path.read_bytes()
                )
            except Exception as e:
                print(f"  ❌ Lỗi đọc PDF: {e}")
                continue

            if not content.strip():
                print("  ⚠ Không trích xuất được nội dung PDF")
                continue

            print(f"  ✓ {len(content):,} ký tự\n")

            # ── Chạy pipeline sinh Q&A ────────────────────────────────────
            print(f"  🤖 Sinh {QUESTIONS_PER_PDF} Q&A...")
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
                )
            except Exception as e:
                print(f"  ❌ Pipeline lỗi: {e}")
                import traceback; traceback.print_exc()
                continue

            elapsed = round(time.time() - t_start, 1)
            n_gen   = len(pipeline_results)
            print(f"\n  ✅ Pipeline xong: {n_gen}/{QUESTIONS_PER_PDF} câu | {elapsed}s\n")

            if n_gen == 0:
                print("  ⚠ Không sinh được câu, bỏ qua PDF này.")
                continue

            # ── Đánh giá Bloom từng câu ───────────────────────────────────
            _eval_qa_list(pipeline_results, pdf_stem, all_rows)

            if pdf_idx < len(PDFS):
                print(f"  ⏳ Chờ 10s trước PDF tiếp theo...")
                time.sleep(10)

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    n_total     = len(all_rows)
    n_correct_2 = sum(1 for r in all_rows if r['is_2llm'])
    n_correct_3 = sum(1 for r in all_rows if r['is_3llm'])

    print(f"\n{'='*72}")
    print(f"  KẾT QUẢ THỰC NGHIỆM 2")
    print(f"{'='*72}")
    print(f"  Tổng câu đánh giá : {n_total}")
    print(f"  ACC₂LLM           : {n_correct_2}/{n_total} = {n_correct_2/n_total*100:.1f}%")
    print(f"  ACC₃LLM           : {n_correct_3}/{n_total} = {n_correct_3/n_total*100:.1f}%")
    print(f"{'='*72}\n")

    # ── Xuất CSV ──────────────────────────────────────────────────────────────
    csv_path = RESULTS_DIR / f'exp2_raw_{timestamp}.csv'
    eval_shorts = [m.split('/')[-1] for m in EVALUATOR_MODELS]
    fieldnames = [
        'idx', 'pdf', 'bloom_level', 'bloom_short', 'sys_bloom_int', 'chapter',
    ]
    for j, m_short in enumerate(eval_shorts):
        fieldnames += [
            f'bloom_pred_{j}', f'bloom_pred_name_{j}',
            f'agree_{j}', f'eval_time_{j}',
        ]
    fieldnames += [
        'n_agree', 'is_2llm', 'is_3llm',
        'process_time_s', 'question', 'answer',
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8-sig',
              errors='replace') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames,
                                extrasaction='ignore', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"  💾 CSV: {csv_path}")

    # ── Xuất Markdown report ──────────────────────────────────────────────────
    report_md  = _generate_report(all_rows, timestamp)
    report_path = RESULTS_DIR / f'exp2_report_{timestamp}.md'
    with open(report_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write(report_md)

    print(f"  📝 Report: {report_path}\n")
    return all_rows


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    run_all()
