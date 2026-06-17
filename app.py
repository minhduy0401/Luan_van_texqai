# app.py – Flask application entry point and route definitions
import sys
import builtins

_orig_print = builtins.print

def safe_print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    encoding = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
    safe_args = []
    for arg in args:
        if isinstance(arg, str):
            safe_args.append(arg.encode(encoding, errors='replace').decode(encoding))
        else:
            safe_args.append(arg)
    _orig_print(*safe_args, **kwargs)

builtins.print = safe_print

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import io
import time
import os
import uuid
import threading
from datetime import datetime, timedelta

# ── One-time download token store (Flutter WebView) ────────────────────────────
_dl_tokens: dict = {}  # token -> (pdf_bytes, filename)
_dl_lock = threading.Lock()

def _store_dl_token(pdf_bytes: bytes, filename: str) -> str:
    """Store PDF bytes and return a short-lived one-time token."""
    token = uuid.uuid4().hex
    with _dl_lock:
        _dl_tokens[token] = (pdf_bytes, filename)
    threading.Timer(120, lambda: _dl_tokens.pop(token, None)).start()
    return token

# ── Project modules ───────────────────────────────────────────────────────────
from config import QUESTION_MODEL, sync_from_db
import config as cfg_module
from utils.bootstrap_config import get_database_uri, get_initial_secret_key, bootstrap_path
from utils.app_settings import (
    get_secret_key,
    get_google_oauth_config,
    get_sepay_api_key,
    seed_default_settings,
)
from extensions import db, login_manager, ai_client, oauth
from models import (
    User, Document, QAResult,
    Agent1EvaluationLog, Agent2EvaluationLog,
    Agent3EvaluationLog,
    UserAuthProvider, Feedback,
)
from utils.bloom import normalize_bloom_level
from utils.helpers import (
    clean_answer_formatting,
    calculate_points_from_bloom,
    _get_pdf_font_name_for_windows,
    _draw_wrapped_pdf_text,
    localize_section_info,
    progress_init_pipeline,
    progress_reading_textbook,
    progress_reading_page,
    progress_textbook_saved,
    progress_saving_results,
    progress_job_complete,
    progress_flash_success,
    progress_error,
)
from services.pdf import extract_pdf_text_plain, extract_pdf_text_with_ocr
from services.pipeline import run_agent_pipeline

# ── Flask app setup ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']               = get_initial_secret_key()
app.config['ENABLE_OCR']               = False
app.config['SQLALCHEMY_DATABASE_URI']  = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
app.config['SESSION_PERMANENT']        = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Tin tưởng proxy headers từ ngrok / nginx / reverse proxy
# x_proto=1 → đọc X-Forwarded-Proto (https) ; x_host=1 → đọc X-Forwarded-Host
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_prefix=1)

db.init_app(app)
login_manager.init_app(app)
oauth.init_app(app)
app.jinja_env.filters['normalize_bloom'] = normalize_bloom_level

from utils.translations import TRANSLATIONS

@app.context_processor
def inject_translations():
    lang = session.get('lang', 'en')
    def translate(text):
        if not text:
            return ""
        txt_str = str(text)
        if lang == 'en':
            return TRANSLATIONS.get(txt_str, {}).get('en', txt_str)
        return TRANSLATIONS.get(txt_str, {}).get('vi', txt_str)
    return dict(t=translate, current_lang=lang)

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ('en', 'vi'):
        session['lang'] = lang
    # Use explicit ?next= param first (iOS WebView doesn't send Referer)
    next_url = request.args.get('next') or request.referrer or url_for('index')
    return redirect(next_url)

def get_lang():
    """Return current UI language ('en' or 'vi')."""
    return session.get('lang', 'en')

def _bi(en, vi):
    """Return en or vi string based on current session language."""
    return en if get_lang() == 'en' else vi

def _fix_enc(text):
    """Fix mojibake (Latin-1/cp1252 mis-decoded UTF-8) in strings from the database."""
    if not text or not isinstance(text, str):
        return text
    _c2b = {}
    for _b in range(0x80, 0x100):
        try:
            _c = bytes([_b]).decode('cp1252')
            if _c not in _c2b:
                _c2b[_c] = _b
        except Exception:
            pass
    for _b in range(0x80, 0xA0):  # C1 control chars from Latin-1
        _c = chr(_b)
        if _c not in _c2b:
            _c2b[_c] = _b
    _eligible = set(_c2b)
    result, i = [], 0
    while i < len(text):
        c = text[i]
        if c not in _eligible:
            result.append(c); i += 1; continue
        j, seg_bytes = i, []
        while j < len(text) and text[j] in _eligible:
            seg_bytes.append(_c2b[text[j]]); j += 1
        fixed, k, consumed = [], 0, 0
        while k < len(seg_bytes):
            b = seg_bytes[k]
            if b < 0x80:
                fixed.append(chr(b)); k += 1; consumed = k; continue
            elif 0xC0 <= b <= 0xDF: needed = 2
            elif 0xE0 <= b <= 0xEF: needed = 3
            elif 0xF0 <= b <= 0xF7: needed = 4
            else: break
            if k + needed > len(seg_bytes): break
            try:
                ch = bytes(seg_bytes[k:k+needed]).decode('utf-8')
                fixed.append(ch); k += needed; consumed = k
            except UnicodeDecodeError: break
        if fixed and consumed > 0:
            result.append(''.join(fixed))
            result.extend(text[i+consumed:j])
            i = j
        else:
            result.append(text[i]); i += 1
    return ''.join(result)

app.jinja_env.filters['fix_enc'] = _fix_enc

def _localize_section_filter(text):
    return localize_section_info(text, get_lang())

app.jinja_env.filters['localize_section'] = _localize_section_filter


def _ensure_google_oauth() -> bool:
    """Đăng ký Google OAuth từ system_settings (có thể gọi lại sau khi admin lưu)."""
    cfg = get_google_oauth_config()
    if not cfg['client_id'] or not cfg['client_secret']:
        return False
    oauth.register(
        name='google',
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
        overwrite=True,
    )
    return True


def _apply_runtime_settings():
    """Nạp cấu hình từ DB sau khi đã kết nối PostgreSQL."""
    from models import SystemSetting
    try:
        seed_default_settings(db.session, SystemSetting)
        sk = get_secret_key(app.config['SECRET_KEY'])
        if sk:
            app.config['SECRET_KEY'] = sk
        ocr = SystemSetting.get('enable_ocr', '0')
        app.config['ENABLE_OCR'] = ocr.lower() in ('1', 'true', 'yes', 'on')
        sync_from_db()
        _ensure_google_oauth()
    except Exception as exc:
        print(f'[WARN] Could not load settings from DB: {exc}', flush=True)


try:
    with app.app_context():
        _apply_runtime_settings()
except Exception:
    pass

print(f"[OK] Database: ...@{app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")
print(f"[OK] Bootstrap: {bootstrap_path()}")
print(f"[OK] AI model: {cfg_module.QUESTION_MODEL}")
print(f"[OK] OCR enabled: {app.config['ENABLE_OCR']}")

# ── In-memory progress store ──────────────────────────────────────────────────
# job_id → { percent, message, done, error, redirect_url, _created_at }
_progress_store: dict = {}

def _cleanup_progress_store():
    """Xóa các job đã done hoặc quá 10 phút để tránh leak RAM."""
    import time as _t
    while True:
        _t.sleep(120)  # kiểm tra mỗi 2 phút
        cutoff = _t.time() - 600  # 10 phút
        keys_to_del = [
            k for k, v in list(_progress_store.items())
            if v.get('done') and v.get('_created_at', 0) < cutoff
        ]
        for k in keys_to_del:
            _progress_store.pop(k, None)

threading.Thread(target=_cleanup_progress_store, daemon=True).start()
print("   Chi phi: ~$0.075/1M tokens (~1,500d/trieu tu)")


# --- ROUTES ---
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('landing.html')

    # Allow logged-in users to view landing page
    if request.args.get('landing') == '1':
        return render_template('landing.html')

    # Flash message forwarded from processing page via query params
    fm = request.args.get('flash_msg')
    fc = request.args.get('flash_cat', 'success')
    if fm:
        flash(fm, fc)
        return redirect(url_for('index'))

    # ── Performance-optimised queries ────────────────────────────────────────
    # Documents: only load the columns needed for the dropdown (skip heavy content field)
    documents = (
        db.session.query(
            Document.id,
            Document.title,
            Document.upload_date,
            Document.user_id,
        )
        .filter_by(user_id=current_user.id)
        .order_by(Document.upload_date.desc())
        .all()
    )

    # QAResults: load all columns except the raw source `content` (not shown in table)
    history = (
        db.session.query(
            QAResult.id,
            QAResult.question,
            QAResult.answer,
            QAResult.bloom_level,
            QAResult.algorithm,
            QAResult.process_time,
            QAResult.section_mapping,
            QAResult.total_points,
            QAResult.sub_points_count,
            QAResult.points_breakdown,
            QAResult.batch_id,
            QAResult.user_id,
            QAResult.document_id,
        )
        .filter_by(user_id=current_user.id)
        .order_by(QAResult.id.desc())
        .all()
    )

    # Nhóm history theo batch_id để hiển thị section
    from types import SimpleNamespace
    doc_map = {d.id: d.title for d in documents}
    batches = []
    seen = {}
    for item in history:
        key = item.batch_id or 'legacy'
        if key not in seen:
            seen[key] = len(batches)
            doc_title = doc_map.get(item.document_id, '') if item.document_id else ''
            batches.append(SimpleNamespace(batch_id=key, doc_title=doc_title, questions=[]))
        batches[seen[key]].questions.append(item)

    return render_template('index.html', history=history, batches=batches, documents=documents)


@app.route('/document/rename', methods=['POST'])
@login_required
def document_rename():
    """Đổi tên gợi nhớ cho giáo trình đã lưu."""
    doc_id   = request.form.get('doc_id', type=int)
    new_name = request.form.get('new_name', '').strip()
    if not doc_id or not new_name:
        return {'ok': False, 'error': 'Thiếu thông tin'}, 400
    doc = Document.query.get(doc_id)
    if not doc or doc.user_id != current_user.id:
        return {'ok': False, 'error': 'Không tìm thấy'}, 404
    doc.title = new_name
    db.session.commit()
    return {'ok': True, 'new_name': new_name}

@app.route('/process', methods=['POST'])
@login_required
def process():
    print("\n[PIPELINE] /process triggered -> starting pipeline execution", flush=True)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    def fail(msg, cat='danger'):
        if is_ajax:
            return jsonify({'error': msg})
        flash(msg, cat)
        return redirect(url_for('index'))

    pdf_file    = request.files.get('pdf_file')
    document_id = request.form.get('document_id')

    # ── Resolve document / PDF bình thường ─────────────────────────────────────
    if document_id:
        doc = Document.query.get(document_id)
        if not doc or doc.user_id != current_user.id:
            return fail('Không tìm thấy tài liệu!')
        # Tài liệu đã có sẵn → không cần đọc lại PDF
        _pdf_binary_data = None
        _content_ready   = doc.content
        _doc_id_ready    = doc.id
        _doc_title_ready = doc.title
        _filename_ready  = doc.filename
    elif pdf_file:
        # Đọc binary ngay để giải phóng file handle, nhưng CHUYỆN OCR vào thread
        _pdf_binary_data = pdf_file.read()
        _content_ready   = None  # sẽ được điền trong thread
        _doc_id_ready    = None
        _doc_title_ready = pdf_file.filename.replace('.pdf', '')
        _filename_ready  = pdf_file.filename
    else:
        return fail('Vui lòng upload file PDF hoặc chọn tài liệu có sẵn!')

    # ── Parse Bloom configs ───────────────────────────────────────────────────
    bloom_name_map = {
        'Bloom 1': 'Bloom 1 (Nhớ)',      'Bloom 2': 'Bloom 2 (Hiểu)',
        'Bloom 3': 'Bloom 3 (Vận dụng)', 'Bloom 4': 'Bloom 4 (Phân tích)',
        'Bloom 5': 'Bloom 5 (Đánh giá)', 'Bloom 6': 'Bloom 6 (Sáng tạo)',
    }
    bloom_configs   = []
    total_questions = 0
    for i in range(1, 7):
        try:
            points = float(request.form.get(f'bloom{i}_points') or 0)
            count  = int(request.form.get(f'bloom{i}_count')  or 0)
        except Exception:
            points, count = 0, 0
        if count > 0:
            bloom_configs.append({
                'bloom_level': bloom_name_map[f'Bloom {i}'],
                'points':      points if points > 0 else None,
                'count':       count,
            })
            total_questions += count

    if total_questions == 0:
        return fail('Vui lòng nhập số lượng câu hỏi cho ít nhất 1 mức Bloom!')

    # ── Kiểm tra credits ─────────────────────────────────────────────────────
    if current_user.credits < total_questions:
        msg = f'Không đủ credits! Cần {total_questions} credits, bạn còn {current_user.credits}.'
        return fail(msg + ' Vui lòng nạp thêm.')

    # Đọc OCR setting
    _ocr_setting = SystemSetting.get('enable_ocr', None)
    if _ocr_setting is not None:
        use_ocr = _ocr_setting in ('1', 'true', 'yes', 'on')
    else:
        use_ocr = app.config.get('ENABLE_OCR', False)

    algo_type = request.form.get('algo_type')

    # ── Tạo job và trả về NGAY để tránh timeout ──────────────────────────────
    import time as _time_now
    job_id = str(uuid.uuid4())
    _ui_lang = get_lang()
    _start_msg = (
        progress_reading_textbook(_ui_lang) if _pdf_binary_data
        else progress_init_pipeline(_ui_lang)
    )
    _progress_store[job_id] = {
        'percent': 0, 'message': _start_msg, 'done': False, 'error': None,
        'phase': 'reading' if _pdf_binary_data else 'pipeline',
        '_created_at': _time_now.time(),
    }

    # Capture values needed in thread
    _user_id       = current_user.id
    _bcfg          = bloom_configs
    _tq            = total_questions
    _at            = algo_type
    _uocr          = use_ocr
    _pdf_data      = _pdf_binary_data
    _content_pre   = _content_ready
    _doc_id_pre    = _doc_id_ready
    _title_pre     = _doc_title_ready
    _fname_pre     = _filename_ready

    def pipeline_thread():
        with app.app_context():
            try:
                def on_progress(pct, msg):
                    _progress_store[job_id]['percent'] = pct
                    _progress_store[job_id]['message'] = msg

                # ── Phase 1: Đọc PDF (nếu upload mới) ─────────────────────────
                if _pdf_data is not None:
                    on_progress(1, progress_reading_textbook(_ui_lang))
                    _progress_store[job_id]['phase'] = 'reading'

                    print(f"\n[PDF] Reading PDF: {_fname_pre} | OCR: {_uocr}")

                    # Callback tiến độ đọc PDF theo trang (0–15%)
                    def on_pdf_page(page_num, total_pages, label=''):
                        pct = int(1 + (page_num / max(total_pages, 1)) * 14)  # 1-15%
                        msg = progress_reading_page(page_num, total_pages, label, _ui_lang)
                        on_progress(pct, msg)

                    if _uocr:
                        content, extraction_stats = extract_pdf_text_with_ocr(
                            _pdf_data, page_callback=on_pdf_page)
                    else:
                        content, extraction_stats = extract_pdf_text_plain(
                            _pdf_data, page_callback=on_pdf_page)

                    total_pages  = extraction_stats.get('total_pages', 0)
                    words_count  = len(content.split())
                    avg_per_page = words_count / total_pages if total_pages > 0 else 0

                    if avg_per_page < 100:
                        flash('⚠️ Nội dung trích xuất thấp (định dạng PDF khó đọc). Nên kích hoạt OCR.', 'warning')

                    if not content.strip():
                        raise ValueError('Không thể trích xuất nội dung từ PDF!')

                    on_progress(15, progress_textbook_saved(_ui_lang))

                    new_doc = Document(title=_title_pre, filename=_fname_pre,
                                       content=content, user_id=_user_id)
                    db.session.add(new_doc)
                    db.session.commit()
                    doc_id = new_doc.id
                else:
                    # Tài liệu đã có sẵn
                    content         = _content_pre
                    doc_id          = _doc_id_pre
                    extraction_stats = {
                        'total_pages':           max(len(content) // 3000, 1),
                        'pages_with_text_layer': max(len(content) // 3000, 1),
                        'pages_with_ocr_text':   0,
                        'ocr_errors':            0,
                    }

                # ── Phase 2: AI Pipeline ──────────────────────────────────────
                _progress_store[job_id]['phase'] = 'pipeline'
                on_progress(16, progress_init_pipeline(_ui_lang))

                # Rải đều tiến độ AI 16– 92%
                def on_pipeline_progress(pct, msg):
                    # pct từ pipeline là 0–100, map sang 16–92%
                    mapped = int(16 + (pct / 100) * 76)
                    on_progress(mapped, msg)

                pipeline_results = run_agent_pipeline(
                    content, extraction_stats, _bcfg, _tq, _at,
                    user_id=_user_id, document_id=doc_id, use_ocr=_uocr,
                    progress_callback=on_pipeline_progress,
                    ui_lang=_ui_lang,
                )

                on_progress(93, progress_saving_results(_ui_lang))
                import time as _time
                _batch_id = _time.strftime('%Y%m%d%H%M%S')
                generated_count = 0
                for res in pipeline_results:
                    try:
                        db.session.add(QAResult(
                            content         = content[:1000],
                            question        = res['question'],
                            answer          = res['answer'],
                            bloom_level     = res['bloom_level'],
                            algorithm       = res['algorithm'],
                            process_time    = res['process_time'],
                            section_mapping = res['section_info'],
                            total_points    = res['total_points'],
                            sub_points_count= res['sub_points_count'],
                            points_breakdown= res['points_breakdown'],
                            batch_id        = _batch_id,
                            user_id         = _user_id,
                            document_id     = doc_id,
                        ))
                        generated_count += 1
                    except Exception as e:
                        print(f"[DB ERROR] Failed to save QA result: {e}")
                db.session.commit()

                # Trừ credits theo đúng số câu tạo được
                if generated_count > 0:
                    user = User.query.get(_user_id)
                    if user:
                        user.credits -= generated_count
                        db.session.commit()
                        print(f"[CREDITS] Deducted {generated_count} credits for user {_user_id} (created {generated_count}/{_tq})")

                _progress_store[job_id] = {
                    'percent':      100,
                    'message':      progress_job_complete(generated_count, _tq, _ui_lang),
                    'done':         True,
                    'error':        None,
                    'flash_msg':    progress_flash_success(generated_count, _tq, _ui_lang),
                    'flash_cat':    'success' if generated_count > 0 else 'warning',
                }
            except Exception as exc:
                import traceback
                traceback.print_exc()
                print(f"[CREDITS] Pipeline failed, did not deduct credits for user {_user_id}")
                _progress_store[job_id] = {
                    'percent': 0,
                    'message': progress_error(exc, _ui_lang),
                    'done':    True,
                    'error':   str(exc),
                }

    t = threading.Thread(target=pipeline_thread, daemon=True)
    t.start()

    # AJAX request → return JSON so the page can show inline progress overlay
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'job_id': job_id})

    return redirect(url_for('processing', job_id=job_id))


@app.route('/processing/<job_id>')
@login_required
def processing(job_id):
    """Render the live progress page."""
    if job_id not in _progress_store:
        flash('Không tìm thấy tiến trình!', 'danger')
        return redirect(url_for('index'))
    return render_template('processing.html', job_id=job_id)


@app.route('/api/progress/<job_id>')
@login_required
def api_progress(job_id):
    """JSON endpoint polled by the progress page."""
    info = _progress_store.get(job_id)
    if not info:
        return jsonify({'error': 'not_found'}), 404
    return jsonify(info)

@app.route('/export-pdf', methods=['POST'])
@login_required
def export_pdf():
    selected_ids_raw = request.form.getlist('selected_question_ids')
    export_mode = request.form.get('export_mode', 'question_only')
    include_answers = export_mode == 'with_answers'

    if not selected_ids_raw:
        flash('Vui lòng chọn ít nhất 1 câu hỏi để xuất PDF!', 'warning')
        return redirect(url_for('index'))

    selected_ids = []
    for item_id in selected_ids_raw:
        try:
            selected_ids.append(int(item_id))
        except ValueError:
            continue

    # Loại trùng, giữ thứ tự người dùng chọn theo danh sách hiển thị
    selected_ids = list(dict.fromkeys(selected_ids))

    if not selected_ids:
        flash('Danh sách câu hỏi không hợp lệ!', 'danger')
        return redirect(url_for('index'))

    selected_questions = (
        QAResult.query
        .filter(QAResult.user_id == current_user.id, QAResult.id.in_(selected_ids))
        .order_by(QAResult.id.asc())
        .all()
    )

    if not selected_questions:
        flash('Không tìm thấy câu hỏi hợp lệ để xuất PDF!', 'danger')
        return redirect(url_for('index'))

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape
    except ImportError:
        flash('Thiếu thư viện reportlab. Vui lòng cài đặt để xuất PDF.', 'danger')
        return redirect(url_for('index'))

    try:
        PAGE_W, PAGE_H = A4
        MARGIN = 48
        CW = PAGE_W - MARGIN * 2           # usable content width
        NUM_W = 30                          # question-number badge column
        ACC_W = 5                           # left accent strip column
        BODY_W = CW - NUM_W - ACC_W        # main text column

        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=52,
            title='Đề kiểm tra',
            author=current_user.username,
        )

        F = _get_pdf_font_name_for_windows()

        # ─── Color palette ───────────────────────────────────────
        def hex_(h): return colors.HexColor(h)
        NAVY      = hex_('#0f172a')
        BLUE      = hex_('#1d4ed8')
        BLUE_LT   = hex_('#3b82f6')
        BLUE_BG   = hex_('#eff6ff')
        BLUE_BD   = hex_('#bfdbfe')
        GREEN     = hex_('#15803d')
        GREEN_BG  = hex_('#f0fdf4')
        GREEN_BD  = hex_('#86efac')
        GREEN_HDR = hex_('#dcfce7')
        BODY      = hex_('#1e293b')
        SLATE     = hex_('#475569')
        MUTED     = hex_('#94a3b8')
        BORDER    = hex_('#e2e8f0')
        BG_LIGHT  = hex_('#f8fafc')
        WHITE     = colors.white

        # ─── Style factory ───────────────────────────────────────
        def S(name, **kw):
            return ParagraphStyle(name, fontName=F, **kw)

        sTitle      = S('sTitle',    fontSize=22, leading=28, alignment=TA_CENTER, textColor=WHITE)
        sSubMeta    = S('sSubMeta',  fontSize=9,  leading=13, alignment=TA_CENTER, textColor=hex_('#cbd5e1'))
        sMetaCell   = S('sMetaCell', fontSize=9.5,leading=13, textColor=SLATE)
        sQNum       = S('sQNum',     fontSize=12, leading=14, alignment=TA_CENTER, textColor=WHITE)
        sQHead      = S('sQHead',    fontSize=12, leading=17, textColor=NAVY)
        sQBody      = S('sQBody',    fontSize=11, leading=18,  textColor=BODY)
        sMeta       = S('sMeta',     fontSize=9,  leading=13, textColor=MUTED)
        sAnsLbl     = S('sAnsLbl',   fontSize=9.5,leading=13, textColor=GREEN)
        sAnsBody    = S('sAnsBody',  fontSize=10.5, leading=17, textColor=BODY)
        sWriteLbl   = S('sWriteLbl', fontSize=9.5, leading=13, textColor=SLATE)

        def esc(t):
            return escape((t or '').strip()).replace('\n', '<br/>')

        # ─── Bloom badge colors ──────────────────────────────────
        BLOOM_CLR = {
            '1': (hex_('#dbeafe'), hex_('#1e40af')),
            '2': (hex_('#dcfce7'), hex_('#166534')),
            '3': (hex_('#fef9c3'), hex_('#854d0e')),
            '4': (hex_('#fce7f3'), hex_('#9d174d')),
            '5': (hex_('#ede9fe'), hex_('#5b21b6')),
            '6': (hex_('#ffedd5'), hex_('#9a3412')),
        }

        lang = session.get('lang', 'en')
        is_en = lang == 'en'

        def make_bloom_badge(bloom_text):
            num = next((c for c in (bloom_text or '') if c.isdigit()), '?')
            bg, fg = BLOOM_CLR.get(num, (BLUE_BG, BLUE))
            bs = S(f'sBadge{num}', fontSize=8, leading=10, alignment=TA_CENTER, textColor=fg)
            trans_bloom = TRANSLATIONS.get(bloom_text, {}).get('en', bloom_text) if is_en else bloom_text
            t = Table([[Paragraph(f'<b>{esc(trans_bloom)}</b>', bs)]], colWidths=[110])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0),(-1,-1), bg),
                ('BOX',           (0,0),(-1,-1), 0.5, fg),
                ('LEFTPADDING',   (0,0),(-1,-1), 6),
                ('RIGHTPADDING',  (0,0),(-1,-1), 6),
                ('TOPPADDING',    (0,0),(-1,-1), 2),
                ('BOTTOMPADDING', (0,0),(-1,-1), 2),
            ]))
            return t

        # ════════════════════════════════════════════════════════
        story = []
        generated_time = time.strftime('%d/%m/%Y  %H:%M:%S')

        if is_en:
            title_text = "EXAM SHEET"
            lbl_date = "Export Date"
            lbl_count = "Total Qs"
            lbl_mode = "Mode"
            mode_text = 'With Answers' if include_answers else 'Questions Only'
            lbl_section = "Textbook Section"
            lbl_suggested_ans = "Suggested Answer"
            lbl_no_ans = "No answer key available"
            lbl_question_no_content = "No question content available"
            lbl_write = "Answer:"
            lbl_points = "points"
            lbl_question = "Question"
        else:
            title_text = "ĐỀ KIỂM TRA"
            lbl_date = "Ngày xuất"
            lbl_count = "Số câu"
            lbl_mode = "Chế độ"
            mode_text = 'Có đáp án' if include_answers else 'Không đáp án'
            lbl_section = "Mục tài liệu"
            lbl_suggested_ans = "Đáp án gợi ý"
            lbl_no_ans = "Không có đáp án"
            lbl_question_no_content = "Không có nội dung câu hỏi"
            lbl_write = "Trả lời:"
            lbl_points = "điểm"
            lbl_question = "Câu"

        # ── Header band ─────────────────────────────────────────
        header_band = Table([
            [Paragraph(title_text, sTitle)],
            [Paragraph(
                f'{lbl_date}: {generated_time}'  \
                f'  &nbsp;·&nbsp;  '\
                f'{lbl_count}: {len(selected_questions)}'  \
                f'  &nbsp;·&nbsp;  '\
                f'{lbl_mode}: {mode_text}',
                sSubMeta
            )],
        ], colWidths=[CW])
        header_band.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), NAVY),
            ('TOPPADDING',    (0,0),(0,0), 20),
            ('BOTTOMPADDING', (0,0),(0,0), 4),
            ('TOPPADDING',    (0,1),(0,1), 2),
            ('BOTTOMPADDING', (0,1),(0,1), 14),
            ('LEFTPADDING',   (0,0),(-1,-1), 16),
            ('RIGHTPADDING',  (0,0),(-1,-1), 16),
        ]))
        story.append(header_band)
        story.append(Spacer(1, 14))

        # ── Questions ────────────────────────────────────────────
        for idx, q in enumerate(selected_questions, 1):
            bloom_text  = normalize_bloom_level(q.bloom_level or '')
            pts         = q.total_points or 0
            q_text      = q.question or lbl_question_no_content

            # Content cell: list of flowables
            cell = []

            # Header row: bloom badge + points (with answers) or just number + points
            if include_answers:
                trans_bloom = TRANSLATIONS.get(bloom_text, {}).get('en', bloom_text) if is_en else bloom_text
                hdr = Paragraph(
                    f'<b>{lbl_question} {idx}:</b>  '
                    f'<font color="#1d4ed8">{esc(trans_bloom)}</font>'  \
                    f'  —  <b>{pts:.2f} {lbl_points}</b>',
                    sQHead
                )
            else:
                hdr = Paragraph(
                    f'<b>{lbl_question} {idx}:</b>  <b>{pts:.2f} {lbl_points}</b>',
                    sQHead
                )
            cell.append(hdr)
            cell.append(Spacer(1, 6))
            cell.append(Paragraph(esc(q_text), sQBody))

            if include_answers and q.section_mapping:
                cell.append(Spacer(1, 4))
                sec_text = localize_section_info(q.section_mapping, 'en' if is_en else 'vi')
                cell.append(Paragraph(
                    f'&#128205; {lbl_section}: <i>{esc(sec_text)}</i>',
                    sMeta
                ))

            # ── Answer / writing area ────────────────────────────
            if include_answers:
                ans_text = q.answer or lbl_no_ans
                cell.append(Spacer(1, 10))

                # Green label header
                ans_lbl_tbl = Table(
                    [[Paragraph(f'<b>&#128161; {lbl_suggested_ans}</b>', sAnsLbl)]],
                    colWidths=[BODY_W]
                )
                ans_lbl_tbl.setStyle(TableStyle([
                    ('BACKGROUND',    (0,0),(-1,-1), GREEN_HDR),
                    ('TOPPADDING',    (0,0),(-1,-1), 4),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 4),
                    ('LEFTPADDING',   (0,0),(-1,-1), 10),
                    ('RIGHTPADDING',  (0,0),(-1,-1), 10),
                    ('LINEBELOW',     (0,0),(-1,-1), 0.5, GREEN_BD),
                ]))
                cell.append(ans_lbl_tbl)

                # Green answer body
                ans_body_tbl = Table(
                    [[Paragraph(esc(ans_text), sAnsBody)]],
                    colWidths=[BODY_W]
                )
                ans_body_tbl.setStyle(TableStyle([
                    ('BACKGROUND',    (0,0),(-1,-1), GREEN_BG),
                    ('BOX',           (0,0),(-1,-1), 0.8, GREEN_BD),
                    ('LEFTPADDING',   (0,0),(-1,-1), 10),
                    ('RIGHTPADDING',  (0,0),(-1,-1), 10),
                    ('TOPPADDING',    (0,0),(-1,-1), 8),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 10),
                ]))
                cell.append(ans_body_tbl)

            else:
                # Blank writing lines
                cell.append(Spacer(1, 8))
                cell.append(Paragraph(f'<b>{lbl_write}</b>', sWriteLbl))
                cell.append(Spacer(1, 2))
                blank_rows = [[Paragraph(' ', sQBody)] for _ in range(5)]
                write_tbl = Table(blank_rows, colWidths=[BODY_W])
                write_tbl.setStyle(TableStyle([
                    *[('LINEBELOW', (0,r),(0,r), 0.4, BORDER) for r in range(5)],
                    ('TOPPADDING',    (0,0),(-1,-1), 10),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 0),
                    ('LEFTPADDING',   (0,0),(-1,-1), 0),
                    ('RIGHTPADDING',  (0,0),(-1,-1), 0),
                ]))
                cell.append(write_tbl)
                cell.append(Spacer(1, 4))

            # ── Assemble card: [num badge | accent | content] ────
            card = Table(
                [[Paragraph(f'<b>{idx}</b>', sQNum), '', cell]],
                colWidths=[NUM_W, ACC_W, BODY_W]
            )
            card.setStyle(TableStyle([
                ('BOX',           (0,0),(-1,-1), 0.8, BORDER),
                ('BACKGROUND',    (0,0),(0,-1), BLUE),
                ('BACKGROUND',    (1,0),(1,-1), BLUE_LT),
                ('VALIGN',        (0,0),(-1,-1), 'TOP'),
                # num col
                ('LEFTPADDING',   (0,0),(0,-1), 2),
                ('RIGHTPADDING',  (0,0),(0,-1), 2),
                ('TOPPADDING',    (0,0),(0,-1), 10),
                ('BOTTOMPADDING', (0,0),(0,-1), 10),
                # accent col
                ('LEFTPADDING',   (1,0),(1,-1), 0),
                ('RIGHTPADDING',  (1,0),(1,-1), 0),
                ('TOPPADDING',    (1,0),(1,-1), 0),
                ('BOTTOMPADDING', (1,0),(1,-1), 0),
                # content col
                ('LEFTPADDING',   (2,0),(2,-1), 12),
                ('RIGHTPADDING',  (2,0),(2,-1), 10),
                ('TOPPADDING',    (2,0),(2,-1), 10),
                ('BOTTOMPADDING', (2,0),(2,-1), 12),
            ]))

            story.append(KeepTogether(card))
            story.append(Spacer(1, 10))

        # ── Footer callback ──────────────────────────────────────
        def _page_footer(canvas_obj, document):
            canvas_obj.saveState()
            canvas_obj.setStrokeColor(BORDER)
            canvas_obj.setLineWidth(0.5)
            canvas_obj.line(MARGIN, 38, PAGE_W - MARGIN, 38)
            canvas_obj.setFont(F, 8)
            canvas_obj.setFillColor(MUTED)
            canvas_obj.drawString(MARGIN, 26, f'Bloom AI  ·  {generated_time}')
            canvas_obj.drawRightString(
                PAGE_W - MARGIN, 26,
                f'Trang {canvas_obj.getPageNumber()}  /  {len(selected_questions)} câu'
            )
            canvas_obj.restoreState()

        doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
        output.seek(0)

        mode_suffix = 'co_dap_an' if include_answers else 'khong_dap_an'
        filename = f"de_kiem_tra_{mode_suffix}_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        if request.headers.get('X-Flutter-DL'):
            token = _store_dl_token(output.getvalue(), filename)
            return jsonify({'token': token, 'filename': filename})
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        print(f"[ERROR] Failed to export PDF: {e}")
        flash(f'Lỗi khi xuất PDF: {str(e)}', 'danger')
        return redirect(url_for('index'))


# ── Xuất đồng thời 2 bản PDF (có & không đáp án) dưới dạng ZIP ──────────────
@app.route('/export-pdf-both', methods=['POST'])
@login_required
def export_pdf_both():
    """Generate both PDF versions and return as a ZIP archive."""
    import zipfile

    selected_ids_raw = request.form.getlist('selected_question_ids')
    if not selected_ids_raw:
        flash('Vui lòng chọn ít nhất 1 câu hỏi để xuất PDF!', 'warning')
        return redirect(url_for('index'))

    selected_ids = []
    for item_id in selected_ids_raw:
        try:
            selected_ids.append(int(item_id))
        except ValueError:
            continue
    selected_ids = list(dict.fromkeys(selected_ids))

    if not selected_ids:
        flash('Danh sách câu hỏi không hợp lệ!', 'danger')
        return redirect(url_for('index'))

    selected_questions = (
        QAResult.query
        .filter(QAResult.user_id == current_user.id, QAResult.id.in_(selected_ids))
        .order_by(QAResult.id.asc())
        .all()
    )

    if not selected_questions:
        flash('Không tìm thấy câu hỏi hợp lệ để xuất PDF!', 'danger')
        return redirect(url_for('index'))

    def _build_pdf(include_answers: bool) -> bytes:
        """Reuse the same build logic as /export-pdf."""
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape

        PAGE_W, PAGE_H = A4
        MARGIN = 48
        CW = PAGE_W - MARGIN * 2
        NUM_W = 30
        ACC_W = 5
        BODY_W = CW - NUM_W - ACC_W

        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=52,
            title='Đề kiểm tra',
            author=current_user.username,
        )

        F = _get_pdf_font_name_for_windows()

        def hex_(h): return colors.HexColor(h)
        NAVY=hex_('#0f172a'); BLUE=hex_('#1d4ed8'); BLUE_LT=hex_('#3b82f6'); BLUE_BG=hex_('#eff6ff')
        BLUE_BD=hex_('#bfdbfe'); GREEN=hex_('#15803d'); GREEN_BG=hex_('#f0fdf4'); GREEN_BD=hex_('#86efac')
        GREEN_HDR=hex_('#dcfce7'); BODY=hex_('#1e293b'); SLATE=hex_('#475569'); MUTED=hex_('#94a3b8')
        BORDER=hex_('#e2e8f0'); WHITE=colors.white

        def S(name, **kw):
            return ParagraphStyle(name + ('_ans' if include_answers else '_noans'), fontName=F, **kw)

        sTitle   = S('sTitle',   fontSize=22, leading=28, alignment=TA_CENTER, textColor=WHITE)
        sSubMeta = S('sSubMeta', fontSize=9,  leading=13, alignment=TA_CENTER, textColor=hex_('#cbd5e1'))
        sQNum    = S('sQNum',    fontSize=12, leading=14, alignment=TA_CENTER, textColor=WHITE)
        sQHead   = S('sQHead',   fontSize=12, leading=17, textColor=NAVY)
        sQBody   = S('sQBody',   fontSize=11, leading=18, textColor=BODY)
        sMeta    = S('sMeta',    fontSize=9,  leading=13, textColor=MUTED)
        sAnsLbl  = S('sAnsLbl',  fontSize=9.5,leading=13, textColor=GREEN)
        sAnsBody = S('sAnsBody', fontSize=10.5, leading=17, textColor=BODY)
        sWriteLbl= S('sWriteLbl',fontSize=9.5, leading=13, textColor=SLATE)

        def esc(t): return escape((t or '').strip()).replace('\n', '<br/>')

        BLOOM_CLR = {
            '1': (hex_('#dbeafe'), hex_('#1e40af')), '2': (hex_('#dcfce7'), hex_('#166534')),
            '3': (hex_('#fef9c3'), hex_('#854d0e')), '4': (hex_('#fce7f3'), hex_('#9d174d')),
            '5': (hex_('#ede9fe'), hex_('#5b21b6')), '6': (hex_('#ffedd5'), hex_('#9a3412')),
        }

        lang = session.get('lang', 'en')
        is_en = lang == 'en'

        if is_en:
            title_text = "EXAM SHEET"
            lbl_date = "Export Date"; lbl_count = "Total Qs"; lbl_mode = "Mode"
            mode_text = 'With Answers' if include_answers else 'Questions Only'
            lbl_section = "Textbook Section"; lbl_suggested_ans = "Suggested Answer"
            lbl_no_ans = "No answer key available"; lbl_question_no_content = "No question content"
            lbl_write = "Answer:"; lbl_points = "points"; lbl_question = "Question"
        else:
            title_text = "ĐỀ KIỂM TRA"
            lbl_date = "Ngày xuất"; lbl_count = "Số câu"; lbl_mode = "Chế độ"
            mode_text = 'Có đáp án' if include_answers else 'Không đáp án'
            lbl_section = "Mục tài liệu"; lbl_suggested_ans = "Đáp án gợi ý"
            lbl_no_ans = "Không có đáp án"; lbl_question_no_content = "Không có nội dung câu hỏi"
            lbl_write = "Trả lời:"; lbl_points = "điểm"; lbl_question = "Câu"

        generated_time = time.strftime('%d/%m/%Y  %H:%M:%S')

        header_band = Table([[Paragraph(title_text, sTitle)],
            [Paragraph(f'{lbl_date}: {generated_time}  &nbsp;·&nbsp;  {lbl_count}: {len(selected_questions)}  &nbsp;·&nbsp;  {lbl_mode}: {mode_text}', sSubMeta)]],
            colWidths=[CW])
        header_band.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),NAVY),
            ('TOPPADDING',(0,0),(0,0),20),('BOTTOMPADDING',(0,0),(0,0),4),
            ('TOPPADDING',(0,1),(0,1),2),('BOTTOMPADDING',(0,1),(0,1),14),
            ('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16),
        ]))

        story = [header_band, Spacer(1, 14)]

        for idx, q in enumerate(selected_questions, 1):
            bloom_text = normalize_bloom_level(q.bloom_level or '')
            pts = q.total_points or 0
            q_text = q.question or lbl_question_no_content
            cell = []

            if include_answers:
                trans_bloom = TRANSLATIONS.get(bloom_text, {}).get('en', bloom_text) if is_en else bloom_text
                hdr = Paragraph(f'<b>{lbl_question} {idx}:</b>  <font color="#1d4ed8">{esc(trans_bloom)}</font>  —  <b>{pts:.2f} {lbl_points}</b>', sQHead)
            else:
                hdr = Paragraph(f'<b>{lbl_question} {idx}:</b>  <b>{pts:.2f} {lbl_points}</b>', sQHead)
            cell.append(hdr)
            cell.append(Spacer(1, 6))
            cell.append(Paragraph(esc(q_text), sQBody))

            if include_answers and q.section_mapping:
                cell.append(Spacer(1, 4))
                sec_text = localize_section_info(q.section_mapping, 'en' if is_en else 'vi')
                cell.append(Paragraph(f'&#128205; {lbl_section}: <i>{esc(sec_text)}</i>', sMeta))

            if include_answers:
                ans_text = q.answer or lbl_no_ans
                cell.append(Spacer(1, 10))
                ans_lbl_tbl = Table([[Paragraph(f'<b>&#128161; {lbl_suggested_ans}</b>', sAnsLbl)]], colWidths=[BODY_W])
                ans_lbl_tbl.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,-1),GREEN_HDR),('TOPPADDING',(0,0),(-1,-1),4),
                    ('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),10),
                    ('RIGHTPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),0.5,GREEN_BD),
                ]))
                ans_body_tbl = Table([[Paragraph(esc(ans_text), sAnsBody)]], colWidths=[BODY_W])
                ans_body_tbl.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,-1),GREEN_BG),('BOX',(0,0),(-1,-1),0.8,GREEN_BD),
                    ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
                    ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),10),
                ]))
                cell.extend([ans_lbl_tbl, ans_body_tbl])
            else:
                cell.append(Spacer(1, 8))
                cell.append(Paragraph(f'<b>{lbl_write}</b>', sWriteLbl))
                cell.append(Spacer(1, 2))
                blank_rows = [[Paragraph(' ', sQBody)] for _ in range(5)]
                write_tbl = Table(blank_rows, colWidths=[BODY_W])
                write_tbl.setStyle(TableStyle([
                    *[('LINEBELOW',(0,r),(0,r),0.4,BORDER) for r in range(5)],
                    ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),0),
                    ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                ]))
                cell.extend([write_tbl, Spacer(1, 4)])

            card = Table([[Paragraph(f'<b>{idx}</b>', sQNum), '', cell]], colWidths=[NUM_W, ACC_W, BODY_W])
            card.setStyle(TableStyle([
                ('BOX',(0,0),(-1,-1),0.8,BORDER),('BACKGROUND',(0,0),(0,-1),BLUE),
                ('BACKGROUND',(1,0),(1,-1),BLUE_LT),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(0,-1),2),('RIGHTPADDING',(0,0),(0,-1),2),
                ('TOPPADDING',(0,0),(0,-1),10),('BOTTOMPADDING',(0,0),(0,-1),10),
                ('LEFTPADDING',(1,0),(1,-1),0),('RIGHTPADDING',(1,0),(1,-1),0),
                ('TOPPADDING',(1,0),(1,-1),0),('BOTTOMPADDING',(1,0),(1,-1),0),
                ('LEFTPADDING',(2,0),(2,-1),12),('RIGHTPADDING',(2,0),(2,-1),10),
                ('TOPPADDING',(2,0),(2,-1),10),('BOTTOMPADDING',(2,0),(2,-1),12),
            ]))
            story.append(KeepTogether(card))
            story.append(Spacer(1, 10))

        def _footer(cv, doc):
            cv.saveState()
            cv.setStrokeColor(BORDER); cv.setLineWidth(0.5)
            cv.line(MARGIN, 38, PAGE_W - MARGIN, 38)
            cv.setFont(F, 8); cv.setFillColor(MUTED)
            cv.drawString(MARGIN, 26, f'Bloom AI  ·  {generated_time}')
            cv.drawRightString(PAGE_W - MARGIN, 26, f'Trang {cv.getPageNumber()}  /  {len(selected_questions)} câu')
            cv.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        output.seek(0)
        return output.getvalue()

    try:
        ts = time.strftime('%Y%m%d_%H%M%S')
        pdf_noans  = _build_pdf(include_answers=False)
        pdf_ans    = _build_pdf(include_answers=True)

        name_noans = f'de_kiem_tra_khong_dap_an_{ts}.pdf'
        name_ans   = f'de_kiem_tra_co_dap_an_{ts}.pdf'
        zip_name   = f'de_kiem_tra_{ts}.zip'

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(name_noans, pdf_noans)
            zf.writestr(name_ans,   pdf_ans)
        zip_buf.seek(0)

        # Flutter app: store token for each PDF then return both tokens
        if request.headers.get('X-Flutter-DL'):
            token_noans = _store_dl_token(pdf_noans, name_noans)
            token_ans   = _store_dl_token(pdf_ans,   name_ans)
            return jsonify({
                'both': True,
                'files': [
                    {'token': token_noans, 'filename': name_noans},
                    {'token': token_ans,   'filename': name_ans},
                ]
            })

        return send_file(zip_buf, mimetype='application/zip', as_attachment=True, download_name=zip_name)

    except Exception as e:
        print(f"[ERROR] Failed to export both PDFs: {e}")
        flash(f'Lỗi khi xuất PDF: {str(e)}', 'danger')
        return redirect(url_for('index'))


# ── Xuất đề thi tự luận chính thức ──────────────────────────────────────────
@app.route('/export-exam', methods=['POST'])
@login_required
def export_exam():
    selected_ids_raw = request.form.getlist('selected_question_ids')
    school_name    = request.form.get('school_name', '').strip()
    faculty_name   = request.form.get('faculty_name', '').strip()
    subject_name   = request.form.get('subject_name', '').strip()
    exam_duration  = request.form.get('exam_duration', '90 phút').strip()
    exam_date_raw  = request.form.get('exam_date', '').strip()
    semester       = request.form.get('semester', '').strip()
    academic_year  = request.form.get('academic_year', '').strip()
    notes          = request.form.get('notes', '').strip()
    include_ans    = bool(request.form.get('include_answer_sheet'))

    if not selected_ids_raw:
        flash('Vui lòng chọn ít nhất 1 câu hỏi!', 'warning')
        return redirect(url_for('index'))

    selected_ids = []
    for item_id in selected_ids_raw:
        try:
            selected_ids.append(int(item_id))
        except ValueError:
            continue

    selected_questions = (
        QAResult.query
        .filter(QAResult.user_id == current_user.id, QAResult.id.in_(selected_ids))
        .order_by(QAResult.id.asc())
        .all()
    )

    if not selected_questions:
        flash('Không tìm thấy câu hỏi hợp lệ!', 'danger')
        return redirect(url_for('index'))

    if exam_date_raw:
        try:
            from datetime import datetime as _dt
            exam_date_str = _dt.strptime(exam_date_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            exam_date_str = exam_date_raw
    else:
        exam_date_str = ''

    total_pts = sum(q.total_points or 0 for q in selected_questions)

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (
            KeepTogether, Paragraph, SimpleDocTemplate, Spacer,
            Table, TableStyle, HRFlowable, PageBreak
        )
        from xml.sax.saxutils import escape as _esc
    except ImportError:
        flash('Thiếu thư viện reportlab.', 'danger')
        return redirect(url_for('index'))

    try:
        PAGE_W, PAGE_H = A4
        ML = MR = 50
        MT = 45
        MB = 45
        CW = PAGE_W - ML - MR

        F  = _get_pdf_font_name_for_windows()
        BLACK  = colors.black
        DGRAY  = colors.HexColor('#1a1a1a')
        MGRAY  = colors.HexColor('#555555')
        LGRAY  = colors.HexColor('#888888')
        BLINE  = colors.HexColor('#cccccc')
        WHITE  = colors.white

        def S(name, **kw):
            base = dict(fontName=F, textColor=BLACK)
            base.update(kw)
            return ParagraphStyle(name, **base)

        # ── styles ─────────────────────────────────────────────
        sSchoolL  = S('sSchoolL',  fontSize=9,  leading=14, alignment=TA_LEFT,   textColor=DGRAY)
        sExamR    = S('sExamR',    fontSize=11, leading=16, alignment=TA_CENTER, textColor=DGRAY)
        sExamBig  = S('sExamBig', fontSize=13, leading=18, alignment=TA_RIGHT, textColor=BLACK)
        sOfficial = S('sOfficial', fontSize=10, leading=14, alignment=TA_LEFT, textColor=BLACK)
        sTimeR    = S('sTimeR',    fontSize=9,  leading=13, alignment=TA_RIGHT,  textColor=MGRAY)
        sNote     = S('sNote',     fontSize=9,  leading=14, alignment=TA_CENTER, textColor=MGRAY)
        sSectionH = S('sSectionH', fontSize=11, leading=16, alignment=TA_LEFT,   textColor=BLACK)
        sQHead    = S('sQHead',    fontSize=11, leading=17, alignment=TA_LEFT,   textColor=BLACK)
        sQBody    = S('sQBody',    fontSize=11, leading=18, alignment=TA_LEFT,   textColor=DGRAY, leftIndent=16)
        sAnsSub   = S('sAnsSub',   fontSize=9,  leading=13, alignment=TA_LEFT,   textColor=MGRAY, leftIndent=16)
        sCenter   = S('sCenter',   fontSize=11, leading=16, alignment=TA_CENTER, textColor=BLACK)
        sDot      = S('sDot',      fontSize=10, leading=16, alignment=TA_LEFT,   textColor=LGRAY)
        sPageHdr  = S('sPageHdr',  fontSize=9,  leading=13, alignment=TA_LEFT,   textColor=MGRAY)
        sWHead    = S('sWHead',    fontSize=10, leading=15, alignment=TA_LEFT,   textColor=BLACK)

        def e(t): return _esc((t or '').strip()).replace('\n', '<br/>')

        generated_time = time.strftime('%d/%m/%Y %H:%M')

        def _build(inc_ans):
            """Build one exam PDF. Returns bytes."""
            out = io.BytesIO()
            doc = SimpleDocTemplate(
                out, pagesize=A4,
                leftMargin=ML, rightMargin=MR,
                topMargin=MT, bottomMargin=MB,
                title='Đề thi tự luận',
                author=current_user.username,
            )
            story = []

            # ══════════════════════════════════════════════════════
            # TRANG 1 – ĐỀ THI
            # ══════════════════════════════════════════════════════

            # ── 1a. Two-column top header ─────────────────────────
            left_lines = []
            if school_name:
                left_lines.append(f'<b>{e(school_name.upper())}</b>')
            if faculty_name:
                left_lines.append(e(faculty_name))
            left_text  = '<br/>'.join(left_lines) if left_lines else ''

            subj_upper = e((subject_name or 'TỰ LUẬN').upper())
            right_top  = f'<b>ĐỀ KIỂM TRA – MÔN: {subj_upper}</b>'
            if semester or academic_year:
                parts = []
                if semester:
                    parts.append(f'Học kỳ: {semester}')
                if academic_year:
                    parts.append(f'Năm học: {academic_year}')
                right_top += f'<br/><font size="9">{e("  –  ".join(parts))}</font>'

            top_hdr = Table([
                [
                    Paragraph(left_text,  sSchoolL),
                    Paragraph(right_top,  sExamBig),
                ]
            ], colWidths=[CW * 0.38, CW * 0.62])
            top_hdr.setStyle(TableStyle([
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
                ('LINEBELOW',     (0,0),(-1,-1), 0.8, BLACK),
                ('TOPPADDING',    (0,0),(-1,-1), 0),
                ('BOTTOMPADDING', (0,0),(-1,-1), 6),
                ('LEFTPADDING',   (0,0),(0,-1), 0),
                ('RIGHTPADDING',  (0,0),(0,-1), 8),
                ('LEFTPADDING',   (1,0),(1,-1), 8),
                ('RIGHTPADDING',  (1,0),(1,-1), 0),
            ]))
            story.append(top_hdr)
            story.append(Spacer(1, 4))

            # ── 1b. Second row: ĐỀ CHÍNH THỨC | time + date ──────
            time_parts = [f'Thời gian làm bài: <b>{e(exam_duration)}</b> (không kể thời gian phát đề)']
            time_parts.append('Ngày kiểm tra: ' + '.' * 36)
            time_text = '<br/>'.join(time_parts)

            row2 = Table([
                [
                    Paragraph('<b>ĐỀ CHÍNH THỨC</b>', sOfficial),
                    Paragraph(time_text, sTimeR),
                ]
            ], colWidths=[CW * 0.3, CW * 0.7])
            row2.setStyle(TableStyle([
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
                ('LINEBELOW',     (0,0),(-1,-1), 0.5, BLACK),
                ('TOPPADDING',    (0,0),(-1,-1), 4),
                ('BOTTOMPADDING', (0,0),(-1,-1), 6),
                ('LEFTPADDING',   (0,0),(0,-1), 0),
                ('RIGHTPADDING',  (1,0),(1,-1), 0),
            ]))
            story.append(row2)
            story.append(Spacer(1, 6))

            # ── 1c. Ghi chú / notes ───────────────────────────────
            if notes:
                story.append(Paragraph(f'<i>({e(notes)})</i>', sNote))
                story.append(Spacer(1, 8))

            # ── 1d. Section header ────────────────────────────────
            section_label = f'TỰ LUẬN ({total_pts:.1f} điểm)'
            story.append(Spacer(1, 4))
            story.append(Paragraph(f'<b>{e(section_label)}</b>', sSectionH))
            story.append(Spacer(1, 10))

            # ── 1e. Questions ─────────────────────────────────────
            for idx, q in enumerate(selected_questions, 1):
                pts    = q.total_points or 0
                q_text = (q.question or '').strip()
                pts_vn = f'{pts:.1f}'.replace('.', ',')
                head   = f'<b>Câu {idx} ({pts_vn} điểm).</b>  {e(q_text)}'
                para   = Paragraph(head, sQHead)
                story.append(KeepTogether([para, Spacer(1, 12)]))

            # ── 1f. Hết ───────────────────────────────────────────
            story.append(Spacer(1, 16))
            story.append(HRFlowable(width=CW * 0.5, thickness=0.6,
                                    color=MGRAY, hAlign='CENTER'))
            story.append(Spacer(1, 4))
            story.append(Paragraph('<b>— Hết —</b>', sCenter))
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width=CW * 0.5, thickness=0.6,
                                    color=MGRAY, hAlign='CENTER'))

            # ══════════════════════════════════════════════════════
            # TRANG 2 – GIẤY LÀM BÀI
            # ══════════════════════════════════════════════════════
            story.append(PageBreak())

            sWF = S('sWF', fontName=F, fontSize=11, leading=16, alignment=TA_LEFT, textColor=BLACK)

            row_truong = Table([[Paragraph('MSSV: ' + '.' * 40, sWF)]], colWidths=[CW])
            row_truong.setStyle(TableStyle([
                ('TOPPADDING',    (0,0),(-1,-1), 3), ('BOTTOMPADDING', (0,0),(-1,-1), 2),
                ('LEFTPADDING',   (0,0),(-1,-1), 0), ('RIGHTPADDING',  (0,0),(-1,-1), 0),
            ]))
            story.append(row_truong)

            row_lop = Table([[Paragraph('Lớp: ' + '.' * 28, sWF)]], colWidths=[CW])
            row_lop.setStyle(TableStyle([
                ('TOPPADDING',    (0,0),(-1,-1), 3), ('BOTTOMPADDING', (0,0),(-1,-1), 2),
                ('LEFTPADDING',   (0,0),(-1,-1), 0), ('RIGHTPADDING',  (0,0),(-1,-1), 0),
            ]))
            story.append(row_lop)

            row_hoten = Table([[Paragraph('Họ tên HS/SV: ' + '.' * 66, sWF)]], colWidths=[CW])
            row_hoten.setStyle(TableStyle([
                ('TOPPADDING',    (0,0),(-1,-1), 3), ('BOTTOMPADDING', (0,0),(-1,-1), 2),
                ('LEFTPADDING',   (0,0),(-1,-1), 0), ('RIGHTPADDING',  (0,0),(-1,-1), 0),
            ]))
            story.append(row_hoten)
            story.append(Spacer(1, 10))

            sGradeHdr = S('sGradeHdr', fontName=F, fontSize=11, leading=15,
                          alignment=TA_CENTER, textColor=BLACK)
            grade_data = [
                [Paragraph('<u><b>Điểm</b></u>', sGradeHdr),
                 Paragraph('<u><b>Nhận xét của thầy giáo, cô giáo</b></u>', sGradeHdr)],
                ['', ''],
            ]
            grade_tbl = Table(grade_data, colWidths=[CW * 0.16, CW * 0.84], rowHeights=[20, 72])
            grade_tbl.setStyle(TableStyle([
                ('BOX',           (0,0),(-1,-1), 0.8, BLACK),
                ('LINEBEFORE',    (1,0),(1,-1),  0.8, BLACK),
                ('LINEBELOW',     (0,0),(-1, 0), 0.8, BLACK),
                ('TOPPADDING',    (0,0),(-1, 0), 3), ('BOTTOMPADDING', (0,0),(-1,0), 3),
                ('TOPPADDING',    (0,1),(-1, 1), 0), ('BOTTOMPADDING', (0,1),(-1,1), 0),
                ('LEFTPADDING',   (0,0),(-1,-1), 4), ('RIGHTPADDING',  (0,0),(-1,-1), 4),
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ]))
            story.append(grade_tbl)
            story.append(Spacer(1, 10))

            DASH_LINE = HRFlowable(width='100%', thickness=0.6, color=MGRAY,
                                   lineCap='butt', dash=(2, 3))
            for _ in range(50):
                story.append(DASH_LINE)
                story.append(Spacer(1, 8))

            story.append(PageBreak())
            for _ in range(68):
                story.append(DASH_LINE)
                story.append(Spacer(1, 8))

            # ══════════════════════════════════════════════════════
            # TRANG ĐÁP ÁN GỢI Ý (tùy chọn)
            # ══════════════════════════════════════════════════════
            if inc_ans:
                story.append(PageBreak())

                ans_top = Table([[
                    Paragraph('<b>ĐÁP ÁN GỢI Ý</b>', S('sAT', fontName=F, fontSize=13,
                                leading=18, alignment=TA_CENTER, textColor=BLACK)),
                ]], colWidths=[CW])
                ans_top.setStyle(TableStyle([
                    ('LINEBELOW',     (0,0),(-1,-1), 1.0, BLACK),
                    ('TOPPADDING',    (0,0),(-1,-1), 0),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 6),
                    ('LEFTPADDING',   (0,0),(-1,-1), 0),
                    ('RIGHTPADDING',  (0,0),(-1,-1), 0),
                ]))
                story.append(ans_top)
                story.append(Paragraph(
                    f'<i>Môn: {e(subject_name or "")}  —  Tổng điểm: {total_pts:.2f}</i>',
                    sNote
                ))
                story.append(Spacer(1, 14))

                for idx, q in enumerate(selected_questions, 1):
                    pts    = q.total_points or 0
                    pts_vn = f'{pts:.1f}'.replace('.', ',')
                    ans    = (q.answer or 'Không có đáp án').strip()
                    story.append(Paragraph(
                        f'<b>Câu {idx} ({pts_vn} điểm).</b>  {e(q.question or "")}',
                        sQHead
                    ))
                    story.append(Spacer(1, 3))
                    story.append(Paragraph(e(ans), S(f'sAns{idx}', fontName=F,
                                  fontSize=10.5, leading=17, alignment=TA_LEFT,
                                  textColor=DGRAY, leftIndent=16,
                                  borderPad=6, borderColor=BLINE,
                                  borderWidth=0, backColor=colors.HexColor('#f7f7f7'))))
                    story.append(Spacer(1, 10))
                    story.append(HRFlowable(width=CW, thickness=0.4, color=BLINE, hAlign='CENTER'))
                    story.append(Spacer(1, 8))

            doc.build(story)
            out.seek(0)
            return out.getvalue()

        # ── Dispatch: single PDF or ZIP of both ───────────────────
        ts = time.strftime('%Y%m%d_%H%M%S')
        safe_subj = (subject_name or 'de_thi').replace(' ', '_')[:30]
        export_mode_val = request.form.get('export_mode', 'single')

        if export_mode_val == 'both':
            import zipfile
            pdf_noans = _build(inc_ans=False)
            pdf_ans   = _build(inc_ans=True)
            name_noans = f"de_thi_{safe_subj}_khong_dap_an_{ts}.pdf"
            name_ans   = f"de_thi_{safe_subj}_co_dap_an_{ts}.pdf"
            zip_name   = f"de_thi_{safe_subj}_{ts}.zip"
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(name_noans, pdf_noans)
                zf.writestr(name_ans,   pdf_ans)
            zip_buf.seek(0)
            if request.headers.get('X-Flutter-DL'):
                token_noans = _store_dl_token(pdf_noans, name_noans)
                token_ans   = _store_dl_token(pdf_ans,   name_ans)
                return jsonify({'both': True, 'files': [
                    {'token': token_noans, 'filename': name_noans},
                    {'token': token_ans,   'filename': name_ans},
                ]})
            return send_file(zip_buf, mimetype='application/zip',
                             as_attachment=True, download_name=zip_name)
        else:
            pdf_bytes = _build(inc_ans=include_ans)
            filename  = f"de_thi_{safe_subj}_{ts}.pdf"
            if request.headers.get('X-Flutter-DL'):
                token = _store_dl_token(pdf_bytes, filename)
                return jsonify({'token': token, 'filename': filename})
            return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                             as_attachment=True, download_name=filename)

    except Exception as e:
        print(f"[ERROR] Failed to export exam: {e}")
        flash(f'Lỗi khi xuất đề thi: {str(e)}', 'danger')
        return redirect(url_for('index'))


# ── One-time token download endpoint (no session needed) ──────────────────────
@app.route('/dl/<token>')
def download_by_token(token):
    with _dl_lock:
        entry = _dl_tokens.pop(token, None)
    if not entry:
        return 'Token không hợp lệ hoặc đã hết hạn.', 404
    file_bytes, filename = entry
    mimetype = 'application/zip' if filename.endswith('.zip') else 'application/pdf'
    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


# ── Local auth ────────────────────────────────────────────────────────────────
# ── Captcha verification helper ───────────────────────────────────────────────
def verify_captcha(response_token):
    captcha_type = SystemSetting.get('captcha_type', 'none')
    if captcha_type == 'none':
        return True

    # v2_invisible dùng cùng API siteverify với v2 checkbox – không cần xử lý khác nhau
    secret_key = SystemSetting.get('recaptcha_secret_key', '').strip()
    if not secret_key or len(secret_key) < 5:
        # Fallback to Google's official public test secret key
        secret_key = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'

    print(f"[CAPTCHA DEBUG] Type: {captcha_type}", flush=True)
    print(f"[CAPTCHA DEBUG] Secret Key (prefix): {secret_key[:10]}...", flush=True)
    print(f"[CAPTCHA DEBUG] Response Token (len): {len(response_token) if response_token else 0}", flush=True)
    print(f"[CAPTCHA DEBUG] Response Token (prefix): {response_token[:30] if response_token else 'None'}...", flush=True)

    if not response_token:
        print("[CAPTCHA DEBUG] FAILED: Response token is empty!", flush=True)
        return False

    import urllib.request
    import urllib.parse
    import json
    import ssl

    url = "https://www.google.com/recaptcha/api/siteverify"
    params = urllib.parse.urlencode({
        'secret': secret_key,
        'response': response_token
    }).encode('utf-8')

    try:
        # Bypass SSL verification for Windows local environments
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, data=params, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            raw_res = response.read().decode('utf-8')
            print(f"[CAPTCHA DEBUG] Google Raw Response: {raw_res}", flush=True)
            res_data = json.loads(raw_res)
            success = res_data.get('success', False)
            print(f"[CAPTCHA DEBUG] Result: {success}", flush=True)
            return success
    except Exception as e:
        print(f"[CAPTCHA DEBUG] Exception error: {e}", flush=True)
        return False


# ── Local auth ────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index', landing='1'))

    allow_forgot = (SystemSetting.get('allow_forgot_password', '0') == '1')
    captcha_type = SystemSetting.get('captcha_type', 'none')
    site_key     = SystemSetting.get('recaptcha_site_key', '').strip()
    if not site_key or len(site_key) < 5:
        site_key = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'

    _is_app = 'TEXTQAI' in request.headers.get('User-Agent', '')
    if _is_app:
        captcha_type = 'none'

    if request.method == 'POST':
        if captcha_type != 'none':
            recaptcha_response = request.form.get('g-recaptcha-response', '')
            if not verify_captcha(recaptcha_response):
                flash(_bi('Captcha verification failed. Please try again.', 'Xác thực Captcha không thành công. Vui lòng thử lại.'), 'danger')
                return render_template('login.html', allow_forgot=allow_forgot, captcha_type=captcha_type, site_key=site_key)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        # Find user then check local provider
        user = User.query.filter_by(username=username).first()
        if user:
            local = UserAuthProvider.query.filter_by(
                user_id=user.id, provider='local'
            ).first()
            if local and check_password_hash(local.password_hash, password):
                login_user(user, remember=True)
                return redirect(url_for('index', landing='1'))
        flash(_bi('Incorrect username or password', 'Sai tài khoản hoặc mật khẩu'), 'danger')

    return render_template('login.html', allow_forgot=allow_forgot, captcha_type=captcha_type, site_key=site_key)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index', landing='1'))

    captcha_type = SystemSetting.get('captcha_type', 'none')
    site_key     = SystemSetting.get('recaptcha_site_key', '').strip()
    if not site_key or len(site_key) < 5:
        site_key = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'

    if 'TEXTQAI' in request.headers.get('User-Agent', ''):
        captcha_type = 'none'

    if request.method == 'POST':
        if captcha_type != 'none':
            recaptcha_response = request.form.get('g-recaptcha-response', '')
            if not verify_captcha(recaptcha_response):
                flash('Xác thực Captcha không thành công. Vui lòng thử lại.', 'danger')
                return render_template('register.html', captcha_type=captcha_type, site_key=site_key)

        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if User.query.filter_by(username=username).first():
            flash(_bi('Username is already taken', 'Tài khoản đã có người đăng ký'), 'danger')
            return redirect(url_for('register'))

        if email and User.query.filter_by(email=email).first():
            flash(_bi('This email is already used by another account', 'Địa chỉ email đã được sử dụng bởi tài khoản khác'), 'danger')
            return redirect(url_for('register'))

        import datetime as _dt
        new_user = User(
            username=username, email=email, display_name=username,
            terms_agreed_at=_dt.datetime.utcnow(),  # checkbox was required before submit
        )
        db.session.add(new_user)
        db.session.flush()  # get new_user.id
        local_provider = UserAuthProvider(
            user_id=new_user.id,
            provider='local',
            password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
        )
        db.session.add(local_provider)
        db.session.commit()
        flash(_bi('Account registered successfully', 'Đã đăng ký tài khoản thành công'), 'success')
        return redirect(url_for('login'))

    return render_template('register.html', captcha_type=captcha_type, site_key=site_key)


# ── SMTP Mail Sender Helper ───────────────────────────────────────────────────
def send_email_smtp(to_email, subject, body_content):
    smtp_server = SystemSetting.get('smtp_server', '').strip()
    smtp_port_str = SystemSetting.get('smtp_port', '587').strip()
    smtp_user   = SystemSetting.get('smtp_user', '').strip()
    smtp_pass   = SystemSetting.get('smtp_password', '').strip()
    sender_name = SystemSetting.get('smtp_sender_name', 'TEXTQAI Support').strip()

    if not smtp_server or not smtp_user or not smtp_pass:
        print(f"[SMTP WARNING] SMTP is not configured. Recipient: {to_email}", flush=True)
        return False, "Hệ thống gửi mail SMTP chưa được cấu hình trong Cài đặt hệ thống."

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        smtp_port = 587

    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header

    msg = MIMEText(body_content, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = Header(f"{sender_name} <{smtp_user}>", 'utf-8')
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        print(f"[SMTP ERROR] Failed to send email to {to_email}: {e}", flush=True)
        return False, str(e)


def generate_random_password(length=8):
    import random
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    allow_forgot = (SystemSetting.get('allow_forgot_password', '0') == '1')
    if not allow_forgot:
        flash(_bi('Password recovery is currently disabled.', 'Chức năng khôi phục mật khẩu tạm thời bị tắt.'), 'danger')
        return redirect(url_for('login'))

    captcha_type = SystemSetting.get('captcha_type', 'none')
    site_key     = SystemSetting.get('recaptcha_site_key', '').strip()
    if not site_key or len(site_key) < 5:
        site_key = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'

    if 'TEXTQAI' in request.headers.get('User-Agent', ''):
        captcha_type = 'none'

    if request.method == 'POST':
        if captcha_type != 'none':
            recaptcha_response = request.form.get('g-recaptcha-response', '')
            if not verify_captcha(recaptcha_response):
                flash('Xác thực Captcha không thành công. Vui lòng thử lại.', 'danger')
                return render_template('forgot_password.html', captcha_type=captcha_type, site_key=site_key)

        email    = request.form.get('email', '').strip()

        if not email:
            flash(_bi('Please enter your registered email.', 'Vui lòng nhập Email đăng ký.'), 'danger')
            return render_template('forgot_password.html', captcha_type=captcha_type, site_key=site_key)

        # Verify email exists
        user = User.query.filter_by(email=email).first()
        if not user:
            flash(_bi('This email is not registered in the system.', 'Địa chỉ email đăng ký không tồn tại trong hệ thống.'), 'danger')
            return render_template('forgot_password.html', captcha_type=captcha_type, site_key=site_key)

        # Generate new random password
        temp_pass = generate_random_password(8)

        # Get or create local provider row
        local = UserAuthProvider.query.filter_by(user_id=user.id, provider='local').first()
        if not local:
            local = UserAuthProvider(user_id=user.id, provider='local')
            db.session.add(local)

        local.password_hash = generate_password_hash(temp_pass, method='pbkdf2:sha256')
        db.session.commit()

        # Send recovery mail via SMTP
        subject = f"Khôi phục mật khẩu tài khoản - TEXTQAI"
        body = (
            f"Chào bạn {user.display},\n\n"
            f"Hệ thống đã nhận được yêu cầu khôi phục mật khẩu của bạn.\n"
            f"Mật khẩu tạm thời mới của bạn là: {temp_pass}\n\n"
            f"Vui lòng đăng nhập bằng mật khẩu tạm thời này và truy cập vào menu 'Đổi mật khẩu' trên thanh công cụ để cập nhật mật khẩu riêng tư của mình.\n\n"
            f"Trân trọng,\n"
            f"Đội ngũ hỗ trợ TEXTQAI"
        )
        
        sent_ok, err_msg = send_email_smtp(email, subject, body)
        if sent_ok:
            flash(_bi('A recovery password has been sent to your email. Please check your inbox!', 'Mật khẩu khôi phục mới đã được gửi vào email của bạn. Vui lòng kiểm tra hộp thư!'), 'success')
        else:
            # Fallback flash for local testing
            print(f"[TEST FALLBACK] New temporary password for {user.username or email} is: {temp_pass}", flush=True)
            flash(_bi(f'Temporary password updated! Since SMTP is not set up, your new password is: {temp_pass}', f'Mật khẩu tạm thời đã cập nhật thành công! Do SMTP chưa được thiết lập, mật khẩu mới của bạn là: {temp_pass}'), 'warning')

        return redirect(url_for('login'))

    return render_template('forgot_password.html', captcha_type=captcha_type, site_key=site_key)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    is_google = UserAuthProvider.query.filter_by(user_id=current_user.id, provider='google').first()
    if is_google:
        flash(_bi('Google accounts cannot use the password change feature.', 'Tài khoản đăng nhập bằng Google không hỗ trợ tính năng đổi mật khẩu.'), 'warning')
        return redirect(url_for('index', landing='1'))

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password     = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or not confirm_password:
            flash(_bi('Please fill in all required fields.', 'Vui lòng điền đầy đủ các thông tin.'), 'danger')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash(_bi('New password and confirmation do not match.', 'Mật khẩu mới và xác nhận mật khẩu không khớp.'), 'danger')
            return render_template('change_password.html')

        local = UserAuthProvider.query.filter_by(user_id=current_user.id, provider='local').first()
        
        # If they registered locally and have a password, verify the current password first
        if local and local.password_hash:
            if not check_password_hash(local.password_hash, current_password):
                flash(_bi('Current password is incorrect.', 'Mật khẩu hiện tại không chính xác.'), 'danger')
                return render_template('change_password.html')

        if not local:
            local = UserAuthProvider(user_id=current_user.id, provider='local')
            db.session.add(local)

        local.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()

        flash(_bi('Password changed successfully!', 'Đổi mật khẩu thành công!'), 'success')
        return redirect(url_for('index'))

    return render_template('change_password.html')


@app.route('/logout')
def logout():
    logout_user()
    next_url = request.args.get('next', '')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(url_for('login'))

# ── Google OAuth routes ────────────────────────────────────────────────────────
@app.route('/login/google')
def login_google():
    """Redirect user to Google for authentication.
    Captcha is NOT required here – Google OAuth is a trusted third-party
    provider that already handles its own bot/abuse protection.
    """
    if not _ensure_google_oauth():
        flash(_bi(
            'Google login is not configured. Please contact the administrator.',
            'Chưa cấu hình đăng nhập Google. Vui lòng liên hệ quản trị viên.',
        ), 'warning')
        return redirect(url_for('login'))

    # Ưu tiên google_redirect_uri trong DB (dùng khi ngrok URL thay đổi)
    redirect_uri = (
        get_google_oauth_config()['redirect_uri']
        or url_for('auth_google_callback', _external=True)
    )
    print(f"[Google OAuth] redirect_uri={redirect_uri}")
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    """Handle Google OAuth callback, create/link user, then log in."""
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        flash(_bi('Google login failed. Please try again.', 'Đăng nhập Google thất bại. Vui lòng thử lại.'), 'danger')
        return redirect(url_for('login'))

    userinfo = token.get('userinfo') or oauth.google.userinfo()
    google_sub   = userinfo['sub']           # stable unique Google ID
    google_email = userinfo.get('email', '')
    google_name  = userinfo.get('name', google_email)

    # 1. Try to find existing Google provider row
    provider_row = UserAuthProvider.query.filter_by(
        provider='google', provider_user_id=google_sub
    ).first()

    if provider_row:
        # Already linked — check if they've agreed to terms
        user = User.query.get(provider_row.user_id)
        if user and not user.terms_agreed_at:
            session['google_pending'] = {
                'sub':        google_sub,
                'email':      google_email,
                'name':       google_name,
                'user_id':    user.id,   # existing user, just need agreement
            }
            return redirect(url_for('google_terms'))
    else:
        # 2. Try to find existing user by email (link Google to that account)
        user = User.query.filter_by(email=google_email).first() if google_email else None

        if not user:
            # 3. Brand-new Google user → require terms agreement before creating account
            session['google_pending'] = {
                'sub':   google_sub,
                'email': google_email,
                'name':  google_name,
            }
            return redirect(url_for('google_terms'))

        # Existing email user linking Google — still require terms if not agreed
        if not user.terms_agreed_at:
            session['google_pending'] = {
                'sub':     google_sub,
                'email':   google_email,
                'name':    google_name,
                'user_id': user.id,
            }
            return redirect(url_for('google_terms'))

        # Already agreed — link Google provider and log in
        provider_row = UserAuthProvider(
            user_id=user.id,
            provider='google',
            provider_user_id=google_sub,
            provider_email=google_email,
        )
        db.session.add(provider_row)
        db.session.commit()

    if not user or not user.is_active:
        flash(_bi('Invalid or locked account.', 'Tài khoản không hợp lệ hoặc đã bị khóa.'), 'danger')
        return redirect(url_for('login'))

    login_user(user, remember=True)
    return redirect(url_for('index', landing='1'))


@app.route('/auth/google/terms', methods=['GET', 'POST'])
def google_terms():
    """Show terms agreement page for new Google users before creating their account."""
    pending = session.get('google_pending')
    if not pending:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if not request.form.get('terms_agree'):
            flash(_bi('You must agree to the Terms of Service and Privacy Policy to continue.',
                      'Bạn phải đồng ý Điều khoản dịch vụ và Chính sách quyền riêng tư để tiếp tục.'), 'danger')
            return redirect(url_for('google_terms'))

        import datetime
        google_sub   = pending['sub']
        google_email = pending['email']
        google_name  = pending['name']
        existing_id  = pending.get('user_id')  # set if user already exists

        if existing_id:
            # Existing user — just record terms agreement (and link Google if not yet linked)
            user = User.query.get(existing_id)
            user.terms_agreed_at = datetime.datetime.utcnow()
            # Link Google provider if not already linked
            already_linked = UserAuthProvider.query.filter_by(
                user_id=existing_id, provider='google'
            ).first()
            if not already_linked:
                db.session.add(UserAuthProvider(
                    user_id=existing_id,
                    provider='google',
                    provider_user_id=google_sub,
                    provider_email=google_email,
                ))
        else:
            # Brand-new user — create account and record terms agreement
            user = User(
                email=google_email,
                display_name=google_name,
                terms_agreed_at=datetime.datetime.utcnow(),
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(UserAuthProvider(
                user_id=user.id,
                provider='google',
                provider_user_id=google_sub,
                provider_email=google_email,
            ))

        db.session.commit()
        session.pop('google_pending', None)
        login_user(user, remember=True)
        return redirect(url_for('index', landing='1'))

    return render_template('google_terms.html', pending=pending)

# ══════════════════════════════════════════════════════════════════════════════
# PAYMENT ROUTES
# ══════════════════════════════════════════════════════════════════════════════
from services.payment import (
    CREDIT_PACKAGES, SUBSCRIPTION_PACKAGES,
    get_package_by_id,
)
from models import CreditPackage, SubscriptionPackage, Transaction, SystemSetting

@app.route('/pricing')
def pricing():
    """Trang bảng giá."""
    # Ưu tiên gói từ DB; fallback hardcode nếu DB chưa có
    db_packages = CreditPackage.query.filter_by(is_active=True).order_by(CreditPackage.id).all()
    if db_packages:
        credit_packages = [
            {'id': p.id, 'name': p.name, 'credits': p.credits,
             'price_vnd': p.price_vnd, 'is_popular': p.is_popular}
            for p in db_packages
        ]
    else:
        credit_packages = CREDIT_PACKAGES

    db_subs = SubscriptionPackage.query.filter_by(is_active=True).order_by(SubscriptionPackage.id).all()
    if db_subs:
        sub_packages = [
            {'id': s.id, 'name': s.name, 'credits': s.credits,
             'price_vnd': s.price_vnd, 'period': s.period}
            for s in db_subs
        ]
    else:
        sub_packages = SUBSCRIPTION_PACKAGES

    enable_vnpay = (SystemSetting.get('enable_vnpay', '1') == '1')
    enable_bank_transfer = (SystemSetting.get('enable_bank_transfer', '1') == '1')

    return render_template('pricing.html',
                           credit_packages=credit_packages,
                           sub_packages=sub_packages,
                           enable_vnpay=enable_vnpay,
                           enable_bank_transfer=enable_bank_transfer)


@app.route('/payment/create', methods=['POST'])
@login_required
def payment_create():
    """Tạo đơn hàng chuyển khoản thủ công và hiển thị thông tin thanh toán."""
    package_id = request.form.get('package_id', type=int)
    pkg_type   = request.form.get('pkg_type', 'credit')   # 'credit' hoặc 'subscription'

    fk_id     = None
    sub_fk_id = None
    pkg       = None

    if pkg_type == 'subscription':
        db_sub = SubscriptionPackage.query.filter_by(id=package_id, is_active=True).first()
        if db_sub:
            pkg = {'name': db_sub.name, 'credits': db_sub.credits, 'price_vnd': db_sub.price_vnd}
            sub_fk_id = db_sub.id
        else:
            pkg = get_package_by_id(package_id)
    else:
        db_pkg = CreditPackage.query.filter_by(id=package_id, is_active=True).first()
        if db_pkg:
            pkg = {'name': db_pkg.name, 'credits': db_pkg.credits, 'price_vnd': db_pkg.price_vnd}
            fk_id = db_pkg.id
        else:
            pkg = get_package_by_id(package_id)

    if not pkg:
        flash(_bi('Invalid package!', 'Gói không hợp lệ!'), 'danger')
        return redirect(url_for('pricing'))

    # Tạo order_code duy nhất
    order_code = int(time.time() * 1000) % 9_000_000_000 + current_user.id

    # Lưu transaction trạng thái pending (chờ admin duyệt)
    txn = Transaction(
        user_id        = current_user.id,
        package_id     = fk_id,
        sub_package_id = sub_fk_id,
        order_code     = str(order_code),
        amount_vnd     = pkg['price_vnd'],
        credits_added  = pkg['credits'],
        status         = 'pending',
    )
    db.session.add(txn)
    db.session.commit()

    # Gửi email thông báo đơn hàng chờ thanh toán
    try:
        user_email = current_user.email
        if user_email:
            subject = f"Thong bao don hang #{txn.order_code} dang cho thanh toan - TEXTQAI"
            body = (
                f"Chào bạn {current_user.display},\n\n"
                f"Đơn hàng nạp credits của bạn đã được tạo thành công.\n"
                f"Mã đơn hàng: {txn.order_code}\n"
                f"Tên gói: {pkg['name']}\n"
                f"Số tiền cần thanh toán: {txn.amount_vnd:,.0f} VNĐ\n"
                f"Số credits nhận được: {txn.credits_added} credits\n"
                f"Nội dung chuyển khoản bắt buộc: DH{txn.order_code}\n\n"
                f"Vui lòng thực hiện chuyển khoản chính xác số tiền và nội dung chuyển khoản trên để hệ thống tự động cộng credits.\n\n"
                f"Trân trọng,\n"
                f"Đội ngũ hỗ trợ TEXTQAI"
            )
            send_email_smtp(user_email, subject, body)
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send pending email: {e}", flush=True)

    return redirect(url_for('payment_pending', order=order_code))


@app.route('/payment/pending')
@login_required
def payment_pending():
    """Hiển thị thông tin chuyển khoản và trạng thái chờ duyệt."""
    order_code = request.args.get('order', '')
    txn = Transaction.query.filter_by(order_code=str(order_code), user_id=current_user.id).first()
    if not txn:
        flash(_bi('Order not found!', 'Không tìm thấy đơn hàng!'), 'danger')
        return redirect(url_for('pricing'))

    # Đọc thông tin ngân hàng từ SystemSetting (fallback sang .env)
    bank_name    = SystemSetting.get('bank_name',    'Vietcombank')
    bank_account = SystemSetting.get('bank_account', '')
    bank_holder  = SystemSetting.get('bank_holder',  '')
    bank_branch  = SystemSetting.get('bank_branch',  '')
    bank_bin     = SystemSetting.get('bank_bin',     '')

    transfer_content = f"DH{txn.order_code}"

    # QR code VietQR (chỉ tạo nếu có bank_bin + bank_account)
    vietqr_url = None
    if bank_bin and bank_account:
        import urllib.parse
        vietqr_url = (
            f"https://img.vietqr.io/image/{bank_bin}-{bank_account}-compact2.png"
            f"?amount={txn.amount_vnd}"
            f"&addInfo={urllib.parse.quote(transfer_content)}"
            f"&accountName={urllib.parse.quote(bank_holder)}"
        )

    return render_template('payment_pending.html',
                           txn=txn,
                           bank_name=bank_name,
                           bank_account=bank_account,
                           bank_holder=bank_holder,
                           bank_branch=bank_branch,
                           transfer_content=transfer_content,
                           vietqr_url=vietqr_url)


@app.route('/payment/cancel')
@login_required
def payment_cancel():
    """Huỷ đơn hàng đang chờ."""
    order_code = request.args.get('order', '')
    txn = Transaction.query.filter_by(order_code=str(order_code), user_id=current_user.id).first()
    if txn and txn.status == 'pending':
        txn.status = 'cancelled'
        db.session.commit()
    flash(_bi('Order cancelled.', 'Đã huỷ đơn hàng.'), 'info')
    return redirect(url_for('pricing'))



# ── SEPAY WEBHOOK ─────────────────────────────────────────────────────────────

@app.route('/payment/sepay/webhook', methods=['POST'])
def payment_sepay_webhook():
    """
    SePay gọi endpoint này mỗi khi phát hiện giao dịch ngân hàng mới.
    Cấu hình tại: my.sepay.vn → Tài khoản ngân hàng → Webhook URL
    Header: Authorization: Apikey <SEPAY_API_KEY>
    """
    # 1. Xác thực token
    sepay_key = get_sepay_api_key()
    auth_header = request.headers.get('Authorization', '')
    expected    = f'Apikey {sepay_key}'
    if sepay_key and auth_header != expected:
        print(f'[SEPAY] Unauthorized auth header: {auth_header!r}', flush=True)
        return jsonify(success=False, message='Unauthorized'), 401

    # 2. Parse payload
    data = request.get_json(silent=True) or {}
    print(f'[SEPAY] Received payload: {data}', flush=True)

    raw_content     = str(data.get('content', '') or data.get('description', ''))
    transfer_content = raw_content.upper()
    try:
        transfer_amount = float(data.get('transferAmount', 0) or data.get('amount', 0))
    except (TypeError, ValueError):
        transfer_amount = 0

    if not transfer_content:
        return jsonify(success=False, message='Missing content'), 400

    # 3. Tìm order_code trong nội dung chuyển khoản (pattern: DH<digits>)
    import re as _re
    match = _re.search(r'DH\s*(\d+)', transfer_content)
    if not match:
        print(f'[SEPAY] No order code in content: {raw_content!r}', flush=True)
        return jsonify(success=True, message='No matching order')  # 200 để SePay không retry

    order_code = match.group(1)
    print(f'[SEPAY] order_code={order_code}, amount={transfer_amount}', flush=True)

    # 4. Tìm transaction trong DB
    txn = Transaction.query.filter_by(order_code=order_code).first()
    if not txn:
        print(f'[SEPAY] Order {order_code} not found in DB', flush=True)
        return jsonify(success=True, message='Order not found')

    if txn.status == 'paid':
        print(f'[SEPAY] Order {order_code} already paid', flush=True)
        return jsonify(success=True, message='Already paid')

    # 5. Kiểm tra số tiền (cho phép sai lệch ±1000đ do phí ngân hàng)
    if transfer_amount > 0 and abs(transfer_amount - txn.amount_vnd) > 1000:
        print(f'[SEPAY] Amount mismatch: got={transfer_amount}, need={txn.amount_vnd}', flush=True)
        return jsonify(
            success=False,
            message=f'Amount mismatch: received {transfer_amount}, expected {txn.amount_vnd}'
        ), 400

    # 6. Cộng credits và cập nhật trạng thái
    txn.status         = 'paid'
    txn.paid_at        = datetime.utcnow()
    txn.payment_method = 'bank_transfer'
    txn.payos_data     = str(data)   # Lưu raw payload để audit

    user = db.session.get(User, txn.user_id)
    if user:
        user.credits += txn.credits_added

    db.session.commit()
    print(f'[SEPAY] PAID order={order_code} +{txn.credits_added} credits user_id={txn.user_id}', flush=True)

    # 7. Gửi email thông báo (non-blocking, lỗi không ảnh hưởng response)
    try:
        if user and user.email:
            subject = f'Don hang #{txn.order_code} da hoan tat - TEXTQAI'
            body = (
                f'Chào bạn {user.display},\n\n'
                f'Chúng tôi đã nhận được thanh toán chuyển khoản của bạn.\n'
                f'Mã đơn hàng  : {txn.order_code}\n'
                f'Số tiền       : {txn.amount_vnd:,.0f} VNĐ\n'
                f'Đã cộng      : +{txn.credits_added} credits\n'
                f'Số dư hiện tại: {user.credits} credits\n\n'
                f'Cảm ơn bạn đã sử dụng dịch vụ!\n\n'
                f'Trân trọng,\nĐội ngũ hỗ trợ TEXTQAI'
            )
            send_email_smtp(user.email, subject, body)
    except Exception as email_err:
        print(f'[SEPAY][EMAIL ERROR] {email_err}', flush=True)

    return jsonify(success=True, message='Credits added successfully')


@app.route('/payment/sepay/test')
@login_required
def payment_sepay_test():
    """Debug endpoint (admin only) – kiểm tra cấu hình SePay webhook."""
    if not current_user.is_admin:
        return jsonify(error='Forbidden'), 403
    webhook_url = url_for('payment_sepay_webhook', _external=True)
    sepay_key = get_sepay_api_key()
    return jsonify(
        webhook_url=webhook_url,
        sepay_key_configured=bool(sepay_key),
        setup_instructions=[
            'Đăng nhập my.sepay.vn',
            'Vào Tài khoản ngân hàng → chọn tài khoản → tab Webhook',
            f'Webhook URL: {webhook_url}',
            f'Authorization Header: Apikey {sepay_key or "(chưa cấu hình trong Admin)"}',
            'Nội dung CK phải chứa: DH<order_code>  (ví dụ: DH123456789)',
        ]
    )


# ── VNPAY ROUTES ──────────────────────────────────────────────────────────────

@app.route('/payment/vnpay/create', methods=['POST'])
@login_required
def payment_vnpay_create():
    """Tạo đơn hàng và chuyển hướng sang cổng VNPAY."""
    from services.payment import vnpay_create_payment_url, vnpay_is_configured, vnpay_return_url_default
    if not vnpay_is_configured():
        flash('VNPAY chưa được cấu hình.', 'danger')
        return redirect(url_for('pricing'))

    package_id = request.form.get('package_id', type=int)
    pkg_type   = request.form.get('pkg_type', 'credit')

    fk_id = sub_fk_id = None
    if pkg_type == 'subscription':
        db_sub = SubscriptionPackage.query.filter_by(id=package_id, is_active=True).first()
        pkg = {'name': db_sub.name, 'credits': db_sub.credits,
               'price_vnd': db_sub.price_vnd} if db_sub else get_package_by_id(package_id)
        if db_sub:
            sub_fk_id = db_sub.id
    else:
        db_pkg = CreditPackage.query.filter_by(id=package_id, is_active=True).first()
        pkg = {'name': db_pkg.name, 'credits': db_pkg.credits,
               'price_vnd': db_pkg.price_vnd} if db_pkg else get_package_by_id(package_id)
        if db_pkg:
            fk_id = db_pkg.id

    if not pkg:
        flash(_bi('Invalid package!', 'Gói không hợp lệ!'), 'danger')
        return redirect(url_for('pricing'))

    import time as _t
    order_code = str(int(_t.time() * 1000) % 9_000_000_000 + current_user.id)

    txn = Transaction(
        user_id        = current_user.id,
        package_id     = fk_id,
        sub_package_id = sub_fk_id,
        order_code     = order_code,
        amount_vnd     = pkg['price_vnd'],
        credits_added  = pkg['credits'],
        status         = 'pending',
        payment_method = 'vnpay',
    )
    db.session.add(txn)
    db.session.commit()

    ip_addr    = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    order_info = f"Nap {pkg['credits']} credits - DH{order_code}"
    return_url = vnpay_return_url_default() or url_for('payment_vnpay_return', _external=True)
    pay_url    = vnpay_create_payment_url(order_code, pkg['price_vnd'],
                                          order_info, ip_addr, return_url)
    return redirect(pay_url)


@app.route('/payment/vnpay/return')
def payment_vnpay_return():
    """VNPAY redirect user về sau khi thanh toán – hiển thị trang kết quả."""
    from services.payment import vnpay_verify_return
    params       = dict(request.args)
    vnp_response = params.get('vnp_ResponseCode', '')
    order_code   = params.get('vnp_TxnRef', '')

    # Xác minh chữ ký – nếu sai thì hiện lỗi ngay
    sig_ok = vnpay_verify_return(params)
    print(f"[VNPAY Return] order={order_code} code={vnp_response} sig_ok={sig_ok}")

    if not sig_ok:
        return render_template('payment_vnpay_result.html',
                               success=False,
                               message='Chữ ký không hợp lệ. Vui lòng liên hệ hỗ trợ.',
                               txn=None)

    txn = Transaction.query.filter_by(order_code=order_code).first()
    if not txn:
        return render_template('payment_vnpay_result.html',
                               success=False,
                               message='Không tìm thấy đơn hàng.',
                               txn=None)

    if vnp_response == '00':
        # Cộng credits nếu IPN chưa xử lý trước
        if txn.status != 'paid':
            txn.status     = 'paid'
            txn.paid_at    = datetime.utcnow()
            txn.payos_data = str(params)
            user = User.query.get(txn.user_id)
            if user:
                user.credits += txn.credits_added
            db.session.commit()
            print(f"[VNPAY Return] [OK] Paid order={order_code} credits={txn.credits_added}")
            
            # Gửi email thông báo nạp thành công
            try:
                if user and user.email:
                    subject = f"Don hang #{txn.order_code} thanh toan thanh cong - TEXTQAI"
                    body = (
                        f"Chào bạn {user.display},\n\n"
                        f"Giao dịch thanh toán qua cổng VNPAY của bạn đã hoàn tất thành công.\n"
                        f"Mã đơn hàng: {txn.order_code}\n"
                        f"Số tiền: {txn.amount_vnd:,.0f} VNĐ\n"
                        f"Đã cộng thành công: +{txn.credits_added} credits vào tài khoản.\n"
                        f"Số dư tài khoản hiện tại của bạn: {user.credits} credits.\n\n"
                        f"Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi.\n\n"
                        f"Trân trọng,\n"
                        f"Đội ngũ hỗ trợ TEXTQAI"
                    )
                    send_email_smtp(user.email, subject, body)
            except Exception as e:
                print(f"[EMAIL ERROR] Failed to send return success email: {e}", flush=True)
        return render_template('payment_vnpay_result.html',
                               success=True,
                               message=f'Thanh toán thành công! Đã cộng {txn.credits_added} credits vào tài khoản.',
                               txn=txn)
    else:
        if txn.status == 'pending':
            txn.status = 'failed'
            db.session.commit()
        # Bảng mã lỗi VNPAY
        err_map = {
            '07': 'Giao dịch bị nghi ngờ gian lận.',
            '09': 'Thẻ/Tài khoản chưa đăng ký dịch vụ.',
            '10': 'Xác thực thẻ thất bại quá 3 lần.',
            '11': 'Giao dịch hết hạn thanh toán.',
            '12': 'Thẻ/Tài khoản bị khóa.',
            '13': 'Sai mật khẩu OTP.',
            '24': 'Khách hàng hủy giao dịch.',
            '51': 'Tài khoản không đủ số dư.',
            '65': 'Vượt hạn mức giao dịch trong ngày.',
            '75': 'Ngân hàng đang bảo trì.',
            '79': 'Sai mật khẩu thanh toán quá số lần quy định.',
        }
        err_msg = err_map.get(vnp_response, f'Thanh toán thất bại (mã lỗi: {vnp_response}).')
        return render_template('payment_vnpay_result.html',
                               success=False,
                               message=err_msg,
                               txn=txn)


@app.route('/payment/vnpay/ipn')
def payment_vnpay_ipn():
    """VNPAY IPN – server-to-server notification (quan trọng hơn return URL)."""
    from services.payment import vnpay_verify_return
    params = dict(request.args)
    print(f"[VNPAY IPN] Received: {params}")

    if not vnpay_verify_return(params):
        return jsonify(RspCode='97', Message='Invalid signature')

    order_code   = params.get('vnp_TxnRef', '')
    vnp_response = params.get('vnp_ResponseCode', '')
    vnp_amount   = int(params.get('vnp_Amount', 0)) // 100

    txn = Transaction.query.filter_by(order_code=order_code).first()
    if not txn:
        return jsonify(RspCode='01', Message='Order not found')
    if txn.status == 'paid':
        return jsonify(RspCode='02', Message='Order already confirmed')
    if abs(vnp_amount - txn.amount_vnd) > 1000:
        return jsonify(RspCode='04', Message='Invalid amount')

    if vnp_response == '00':
        txn.status         = 'paid'
        txn.paid_at        = datetime.utcnow()
        txn.payment_method = 'vnpay'
        txn.payos_data     = str(params)
        user = User.query.get(txn.user_id)
        if user:
            user.credits += txn.credits_added
        db.session.commit()
        print(f"[VNPAY IPN] [OK] Paid: order={order_code} credits={txn.credits_added} user={txn.user_id}")
        
        # Gửi email thông báo nạp thành công
        try:
            if user and user.email:
                subject = f"Don hang #{txn.order_code} thanh toan thanh cong - TEXTQAI"
                body = (
                    f"Chào bạn {user.display},\n\n"
                    f"Giao dịch thanh toán qua cổng VNPAY của bạn đã hoàn tất thành công.\n"
                    f"Mã đơn hàng: {txn.order_code}\n"
                    f"Số tiền: {txn.amount_vnd:,.0f} VNĐ\n"
                    f"Đã cộng thành công: +{txn.credits_added} credits vào tài khoản.\n"
                    f"Số dư tài khoản hiện tại của bạn: {user.credits} credits.\n\n"
                    f"Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi.\n\n"
                    f"Trân trọng,\n"
                    f"Đội ngũ hỗ trợ TEXTQAI"
                )
                send_email_smtp(user.email, subject, body)
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send IPN success email: {e}", flush=True)
    else:
        txn.status = 'failed'
        db.session.commit()

    return jsonify(RspCode='00', Message='Confirm success')


@app.route('/payment/history')
@login_required
def payment_history():
    """Lịch sử giao dịch của user."""
    txns = Transaction.query.filter_by(user_id=current_user.id)\
                            .order_by(Transaction.created_at.desc()).limit(50).all()
    return render_template('payment_history.html', transactions=txns)


@app.route('/payment/status')
@login_required
def payment_status():
    """Endpoint JSON để frontend polling trạng thái đơn hàng."""
    order_code = request.args.get('order', '')
    txn = Transaction.query.filter_by(order_code=str(order_code), user_id=current_user.id).first()
    if not txn:
        return jsonify({'status': 'not_found'}), 404
    return jsonify({'status': txn.status, 'credits': current_user.credits})


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════
from functools import wraps
from sqlalchemy import func as sqlfunc

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash(_bi('You do not have permission to access this page.', 'Bạn không có quyền truy cập trang này.'), 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    from datetime import timedelta
    today = datetime.utcnow().date()
    week_ago  = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    stats = {
        'total_users':    User.query.count(),
        'users_today':    User.query.filter(sqlfunc.date(User.created_at) == today).count(),
        'users_week':     User.query.filter(User.created_at >= week_ago).count(),
        'total_questions': QAResult.query.count(),
        'questions_week': QAResult.query.count(),  # simplified
        'total_revenue':  db.session.query(sqlfunc.sum(Transaction.amount_vnd)).filter_by(status='paid').scalar() or 0,
        'revenue_month':  db.session.query(sqlfunc.sum(Transaction.amount_vnd)).filter(
            Transaction.status == 'paid', Transaction.paid_at >= month_ago).scalar() or 0,
        'total_txn':      Transaction.query.count(),
        'paid_txn':       Transaction.query.filter_by(status='paid').count(),
        'pending_txn':    Transaction.query.filter_by(status='pending').count(),
        'total_docs':     Document.query.count(),
    }

    # Bloom distribution
    bloom_stats = db.session.query(
        QAResult.bloom_level, sqlfunc.count(QAResult.id)
    ).group_by(QAResult.bloom_level).all()

    # Recent transactions
    recent_txns = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()

    # Top users by questions
    top_users = db.session.query(
        User, sqlfunc.count(QAResult.id).label('q_count')
    ).join(QAResult, QAResult.user_id == User.id)\
     .group_by(User.id).order_by(sqlfunc.count(QAResult.id).desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           stats=stats,
                           bloom_stats=bloom_stats,
                           recent_txns=recent_txns,
                           top_users=top_users)


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    q        = request.args.get('q', '').strip()
    status   = request.args.get('status', '')
    page     = request.args.get('page', 1, type=int)

    query = User.query
    if q:
        query = query.filter(
            User.username.ilike(f'%{q}%') |
            User.email.ilike(f'%{q}%') |
            User.display_name.ilike(f'%{q}%')
        )
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'locked':
        query = query.filter_by(is_active=False)
    elif status == 'admin':
        query = query.filter_by(is_admin=True)

    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=users, q=q, status=status)


@app.route('/admin/users/<int:user_id>')
@login_required
@admin_required
def admin_user_detail(user_id):
    user  = User.query.get_or_404(user_id)
    txns  = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).limit(20).all()
    questions = QAResult.query.filter_by(user_id=user_id).order_by(QAResult.id.desc()).limit(20).all()
    return render_template('admin/user_detail.html', user=user, txns=txns, questions=questions)


@app.route('/admin/users/<int:user_id>/credits', methods=['POST'])
@login_required
@admin_required
def admin_adjust_credits(user_id):
    user   = User.query.get_or_404(user_id)
    delta  = request.form.get('delta', type=int, default=0)
    reason = request.form.get('reason', '').strip()
    if delta != 0:
        user.credits = max(0, user.credits + delta)
        db.session.commit()
        action = f'+{delta}' if delta > 0 else str(delta)
        flash(f'Đã {action} credits cho {user.display}. Lý do: {reason or "Không có"}', 'success')
    return redirect(url_for('admin_user_detail', user_id=user_id))


@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Không thể khoá chính mình!', 'danger')
        return redirect(url_for('admin_user_detail', user_id=user_id))
    user.is_active = not user.is_active
    db.session.commit()
    status = 'mở khoá' if user.is_active else 'khoá'
    flash(f'Đã {status} tài khoản {user.display}.', 'success')
    return redirect(url_for('admin_user_detail', user_id=user_id))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Không thể xóa chính mình!', 'danger')
        return redirect(url_for('admin_user_detail', user_id=user_id))
    if user.is_admin:
        flash('Không thể xóa tài khoản Admin!', 'danger')
        return redirect(url_for('admin_user_detail', user_id=user_id))

    name = user.display
    # Delete all related data
    QAResult.query.filter_by(user_id=user_id).delete()
    Transaction.query.filter_by(user_id=user_id).delete()
    Document.query.filter_by(user_id=user_id).delete()
    UserAuthProvider.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f'Đã xóa tài khoản "{name}" và toàn bộ dữ liệu liên quan.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/transactions')
@login_required
@admin_required
def admin_transactions():
    status    = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    page      = request.args.get('page', 1, type=int)

    query = Transaction.query
    if status:
        query = query.filter_by(status=status)
    if date_from:
        try:
            query = query.filter(Transaction.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import timedelta
            query = query.filter(Transaction.created_at < datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            pass

    total_revenue = db.session.query(sqlfunc.sum(Transaction.amount_vnd)).filter_by(status='paid').scalar() or 0
    txns = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/transactions.html',
                           txns=txns, status=status,
                           date_from=date_from, date_to=date_to,
                           total_revenue=total_revenue)


@app.route('/admin/transactions/export-csv')
@login_required
@admin_required
def admin_export_transactions_csv():
    import csv
    status    = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')

    query = Transaction.query
    if status:
        query = query.filter_by(status=status)
    if date_from:
        try:
            query = query.filter(Transaction.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import timedelta
            query = query.filter(Transaction.created_at < datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            pass

    txns = query.order_by(Transaction.created_at.desc()).all()

    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel UTF-8
    import csv as _csv
    writer = _csv.writer(output)
    writer.writerow(['ID', 'User', 'Email', 'Order Code', 'Số tiền (VNĐ)', 'Credits', 'Trạng thái', 'PTTT', 'Ngày tạo', 'Ngày thanh toán'])
    for t in txns:
        writer.writerow([
            t.id,
            t.user.display if t.user else '',
            t.user.email if t.user else '',
            t.order_code,
            t.amount_vnd,
            t.credits_added,
            t.status,
            t.payment_method or '',
            t.created_at.strftime('%d/%m/%Y %H:%M') if t.created_at else '',
            t.paid_at.strftime('%d/%m/%Y %H:%M') if t.paid_at else '',
        ])

    filename = f"transactions_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    return app.response_class(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/admin/transactions/<int:txn_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_transaction(txn_id):
    """Admin duyệt đơn hàng thủ công – cộng credits cho user."""
    txn = Transaction.query.get_or_404(txn_id)
    if txn.status == 'paid':
        flash('Đơn hàng này đã được duyệt rồi.', 'warning')
        return redirect(url_for('admin_transactions'))

    txn.status         = 'paid'
    txn.paid_at        = datetime.utcnow()
    txn.payment_method = 'manual'

    user = User.query.get(txn.user_id)
    if user:
        user.credits += txn.credits_added

    db.session.commit()

    # Gửi email thông báo nạp thành công
    try:
        if user and user.email:
            subject = f"Don hang #{txn.order_code} da hoan tat - TEXTQAI"
            body = (
                f"Chào bạn {user.display},\n\n"
                f"Giao dịch nạp credits của bạn đã được quản trị viên phê duyệt thành công.\n"
                f"Mã đơn hàng: {txn.order_code}\n"
                f"Số tiền: {txn.amount_vnd:,.0f} VNĐ\n"
                f"Đã cộng thành công: +{txn.credits_added} credits vào tài khoản.\n"
                f"Số dư tài khoản hiện tại của bạn: {user.credits} credits.\n\n"
                f"Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi.\n\n"
                f"Trân trọng,\n"
                f"Đội ngũ hỗ trợ TEXTQAI"
            )
            send_email_smtp(user.email, subject, body)
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send approve success email: {e}", flush=True)

    flash(f'Đã duyệt đơn #{txn.order_code} – cộng {txn.credits_added} credits cho {user.display if user else "user"}.', 'success')
    return redirect(url_for('admin_transactions'))


@app.route('/admin/transactions/<int:txn_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_reject_transaction(txn_id):
    """Admin từ chối đơn hàng."""
    txn = Transaction.query.get_or_404(txn_id)
    if txn.status not in ('pending',):
        flash('Chỉ có thể từ chối đơn đang chờ.', 'warning')
        return redirect(url_for('admin_transactions'))

    txn.status = 'failed'
    db.session.commit()
    flash(f'Đã từ chối đơn #{txn.order_code}.', 'info')
    return redirect(url_for('admin_transactions'))


@app.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    # Bloom distribution
    bloom_stats = db.session.query(
        QAResult.bloom_level, sqlfunc.count(QAResult.id)
    ).group_by(QAResult.bloom_level).order_by(sqlfunc.count(QAResult.id).desc()).all()

    # Algorithm distribution (AI vs fallback)
    algo_stats = db.session.query(
        QAResult.algorithm, sqlfunc.count(QAResult.id)
    ).group_by(QAResult.algorithm).order_by(sqlfunc.count(QAResult.id).desc()).all()

    # Avg process time
    avg_time = db.session.query(sqlfunc.avg(QAResult.process_time)).scalar() or 0

    # Top documents
    top_docs = db.session.query(
        Document, sqlfunc.count(QAResult.id).label('q_count')
    ).join(QAResult, QAResult.document_id == Document.id)\
     .group_by(Document.id).order_by(sqlfunc.count(QAResult.id).desc()).limit(10).all()

    # Top users
    top_users = db.session.query(
        User, sqlfunc.count(QAResult.id).label('q_count')
    ).join(QAResult, QAResult.user_id == User.id)\
     .group_by(User.id).order_by(sqlfunc.count(QAResult.id).desc()).limit(10).all()

    # Questions per day (last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_questions = db.session.query(
        sqlfunc.date(QAResult.id), sqlfunc.count(QAResult.id)
    ).filter(User.created_at >= thirty_days_ago).all()

    return render_template('admin/stats.html',
                           bloom_stats=bloom_stats,
                           algo_stats=algo_stats,
                           avg_time=avg_time,
                           top_docs=top_docs,
                           top_users=top_users)


@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'general':
            SystemSetting.set('allow_register',    request.form.get('allow_register', '0'))
            SystemSetting.set('default_credits',   request.form.get('default_credits', '5'))
            SystemSetting.set('enable_ocr',        request.form.get('enable_ocr', '0'))
            app.config['ENABLE_OCR'] = request.form.get('enable_ocr', '0') in ('1', 'on')
            flash('Đã lưu cài đặt chung.', 'success')

        elif action == 'ai_model':
            # 1. Update API Keys
            openrouter_key = request.form.get('openrouter_api_key', '').strip()
            openai_key     = request.form.get('openai_api_key', '').strip()
            gemini_key     = request.form.get('gemini_api_key', '').strip()
            
            if openrouter_key: SystemSetting.set('openrouter_api_key', openrouter_key)
            if openai_key:     SystemSetting.set('openai_api_key',     openai_key)
            if gemini_key:     SystemSetting.set('gemini_api_key',     gemini_key)

            # 1.1. Update provider-specific models
            openrouter_model = request.form.get('openrouter_model', '').strip()
            openai_model     = request.form.get('openai_model', '').strip()
            gemini_model     = request.form.get('gemini_model', '').strip()

            if openrouter_model: SystemSetting.set('openrouter_model', openrouter_model)
            if openai_model:     SystemSetting.set('openai_model',     openai_model)
            if gemini_model:     SystemSetting.set('gemini_model',     gemini_model)
            
            # 2. Check which provider was activated
            activated = request.form.get('activate_provider', 'save_model')
            if activated in ('openrouter', 'openai', 'gemini'):
                SystemSetting.set('active_ai_provider', activated)
                flash(f'Đã kích hoạt nhà cung cấp: {activated.upper()}!', 'success')
            
            # 3. Handle model name save
            new_model = None
            if activated == 'openrouter':
                new_model = openrouter_model or SystemSetting.get('openrouter_model', 'google/gemini-2.5-flash-lite')
            elif activated == 'openai':
                new_model = openai_model or SystemSetting.get('openai_model', 'gpt-4o-mini')
            elif activated == 'gemini':
                new_model = gemini_model or SystemSetting.get('gemini_model', 'gemini-2.5-flash')
            else:
                new_model = request.form.get('ai_model', '').strip()

            if new_model:
                SystemSetting.set('ai_model', new_model)
                cfg_module.sync_from_db()
                flash(f'Đã đổi model AI hoạt động thành: {new_model}', 'success')

        elif action == 'integrations':
            secret_key = request.form.get('secret_key', '').strip()
            if secret_key:
                SystemSetting.set('secret_key', secret_key)
                app.config['SECRET_KEY'] = secret_key
            google_id = request.form.get('google_client_id', '').strip()
            google_secret = request.form.get('google_client_secret', '').strip()
            if google_id:
                SystemSetting.set('google_client_id', google_id)
            if google_secret:
                SystemSetting.set('google_client_secret', google_secret)
            SystemSetting.set('google_redirect_uri', request.form.get('google_redirect_uri', '').strip())
            vnpay_tmn = request.form.get('vnpay_tmn_code', '').strip()
            vnpay_hash = request.form.get('vnpay_hash_secret', '').strip()
            if vnpay_tmn:
                SystemSetting.set('vnpay_tmn_code', vnpay_tmn)
            if vnpay_hash:
                SystemSetting.set('vnpay_hash_secret', vnpay_hash)
            SystemSetting.set('vnpay_url', request.form.get('vnpay_url', '').strip()
                                or 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html')
            SystemSetting.set('vnpay_return_url', request.form.get('vnpay_return_url', '').strip())
            sepay_key = request.form.get('sepay_api_key', '').strip()
            if sepay_key:
                SystemSetting.set('sepay_api_key', sepay_key)
            _ensure_google_oauth()
            flash('Đã lưu cấu hình tích hợp (OAuth, VNPAY, SePay).', 'success')

        elif action == 'payment':
            SystemSetting.set('bank_name',     request.form.get('bank_name',     '').strip())
            SystemSetting.set('bank_bin',      request.form.get('bank_bin',      '').strip())
            SystemSetting.set('bank_account',  request.form.get('bank_account',  '').strip())
            SystemSetting.set('bank_holder',   request.form.get('bank_holder',   '').strip())
            SystemSetting.set('bank_branch',   request.form.get('bank_branch',   '').strip())
            SystemSetting.set('enable_vnpay',  request.form.get('enable_vnpay',  '0'))
            SystemSetting.set('enable_bank_transfer', request.form.get('enable_bank_transfer', '0'))
            flash('Đã lưu cài đặt thanh toán.', 'success')

        elif action == 'security':
            SystemSetting.set('allow_forgot_password', request.form.get('allow_forgot_password', '0'))
            SystemSetting.set('captcha_type',          request.form.get('captcha_type', 'none'))
            SystemSetting.set('recaptcha_site_key',    request.form.get('recaptcha_site_key', '').strip())
            SystemSetting.set('recaptcha_secret_key',  request.form.get('recaptcha_secret_key', '').strip())
            SystemSetting.set('smtp_server',           request.form.get('smtp_server', '').strip())
            SystemSetting.set('smtp_port',             request.form.get('smtp_port', '587').strip())
            SystemSetting.set('smtp_sender_name',      request.form.get('smtp_sender_name', 'TEXTQAI Support').strip())
            SystemSetting.set('smtp_user',             request.form.get('smtp_user', '').strip())
            SystemSetting.set('smtp_password',         request.form.get('smtp_password', '').strip())
            flash('Đã lưu cấu hình bảo mật và Captcha.', 'success')

        elif action == 'package':
            pkg_action = request.form.get('pkg_action')
            if pkg_action == 'add':
                name       = request.form.get('pkg_name', '').strip()
                credits    = request.form.get('pkg_credits', type=int, default=0)
                price_vnd  = request.form.get('pkg_price', type=int, default=0)
                is_popular = bool(request.form.get('pkg_popular'))
                if name and credits > 0 and price_vnd > 0:
                    db.session.add(CreditPackage(
                        name=name, credits=credits, price_vnd=price_vnd,
                        is_active=True, is_popular=is_popular
                    ))
                    db.session.commit()
                    flash(f'Đã thêm gói "{name}".', 'success')
            elif pkg_action == 'toggle':
                pkg_id = request.form.get('pkg_id', type=int)
                pkg = CreditPackage.query.get(pkg_id)
                if pkg:
                    pkg.is_active = not pkg.is_active
                    db.session.commit()
                    flash(f'Đã {"bật" if pkg.is_active else "ẩn"} gói {pkg.name}.', 'success')
            elif pkg_action == 'delete':
                pkg_id = request.form.get('pkg_id', type=int)
                pkg = CreditPackage.query.get(pkg_id)
                if pkg:
                    db.session.delete(pkg)
                    db.session.commit()
                    flash(f'Đã xoá gói.', 'success')
            elif pkg_action == 'edit':
                pkg_id    = request.form.get('pkg_id', type=int)
                pkg = CreditPackage.query.get(pkg_id)
                if pkg:
                    new_name    = request.form.get('pkg_name', '').strip()
                    new_credits = request.form.get('pkg_credits', type=int)
                    new_price   = request.form.get('pkg_price', type=int)
                    new_popular = bool(request.form.get('pkg_popular'))
                    if new_name:   pkg.name       = new_name
                    if new_credits and new_credits > 0: pkg.credits    = new_credits
                    if new_price   and new_price > 0:   pkg.price_vnd  = new_price
                    pkg.is_popular = new_popular
                    db.session.commit()
                    flash(f'Đã cập nhật gói "{pkg.name}".', 'success')

        elif action == 'sub_package':
            sub_action = request.form.get('sub_action')
            if sub_action == 'add':
                name      = request.form.get('sub_name', '').strip()
                credits   = request.form.get('sub_credits', type=int, default=0)
                price_vnd = request.form.get('sub_price', type=int, default=0)
                period    = request.form.get('sub_period', 'tháng').strip() or 'tháng'
                if name and credits > 0 and price_vnd > 0:
                    db.session.add(SubscriptionPackage(
                        name=name, credits=credits, price_vnd=price_vnd,
                        period=period, is_active=True,
                    ))
                    db.session.commit()
                    flash(f'Đã thêm gói thuê bao "{name}".', 'success')
            elif sub_action == 'toggle':
                sub_id = request.form.get('sub_id', type=int)
                sub = SubscriptionPackage.query.get(sub_id)
                if sub:
                    sub.is_active = not sub.is_active
                    db.session.commit()
                    flash(f'Đã {"bật" if sub.is_active else "ẩn"} gói {sub.name}.', 'success')
            elif sub_action == 'delete':
                sub_id = request.form.get('sub_id', type=int)
                sub = SubscriptionPackage.query.get(sub_id)
                if sub:
                    db.session.delete(sub)
                    db.session.commit()
                    flash('Đã xoá gói thuê bao.', 'success')
            elif sub_action == 'edit':
                sub_id = request.form.get('sub_id', type=int)
                sub = SubscriptionPackage.query.get(sub_id)
                if sub:
                    new_name    = request.form.get('sub_name', '').strip()
                    new_credits = request.form.get('sub_credits', type=int)
                    new_price   = request.form.get('sub_price', type=int)
                    new_period  = request.form.get('sub_period', '').strip()
                    if new_name:                            sub.name      = new_name
                    if new_credits and new_credits > 0:    sub.credits   = new_credits
                    if new_price   and new_price > 0:      sub.price_vnd = new_price
                    if new_period:                          sub.period    = new_period
                    db.session.commit()
                    flash(f'Đã cập nhật gói thuê bao "{sub.name}".', 'success')

        return redirect(url_for('admin_settings'))

    packages  = CreditPackage.query.order_by(CreditPackage.id).all()
    # Auto-seed credit packages if DB is empty
    if not packages:
        for p in CREDIT_PACKAGES:
            db.session.add(CreditPackage(
                name=p['name'], credits=p['credits'],
                price_vnd=p['price_vnd'], is_active=True,
                is_popular=p.get('is_popular', False),
            ))
        db.session.commit()
        packages = CreditPackage.query.order_by(CreditPackage.id).all()

    sub_packages = SubscriptionPackage.query.order_by(SubscriptionPackage.id).all()
    # Auto-seed subscription packages if DB is empty
    if not sub_packages:
        for p in SUBSCRIPTION_PACKAGES:
            db.session.add(SubscriptionPackage(
                id=p['id'], name=p['name'], credits=p['credits'],
                price_vnd=p['price_vnd'], period=p.get('period', 'tháng'), is_active=True,
            ))
        db.session.commit()
        sub_packages = SubscriptionPackage.query.order_by(SubscriptionPackage.id).all()

    settings  = {
        'allow_register':  SystemSetting.get('allow_register', '1'),
        'default_credits': SystemSetting.get('default_credits', '5'),
        'enable_ocr':      SystemSetting.get('enable_ocr', '0'),
        'ai_model':        SystemSetting.get('ai_model', cfg_module.QUESTION_MODEL),
        'bank_name':       SystemSetting.get('bank_name',    ''),
        'bank_bin':        SystemSetting.get('bank_bin',     ''),
        'bank_account':    SystemSetting.get('bank_account', ''),
        'bank_holder':     SystemSetting.get('bank_holder',  ''),
        'bank_branch':     SystemSetting.get('bank_branch',  ''),
        'enable_vnpay':    SystemSetting.get('enable_vnpay',  '1'),
        'enable_bank_transfer': SystemSetting.get('enable_bank_transfer', '1'),
        'allow_forgot_password': SystemSetting.get('allow_forgot_password', '0'),
        'captcha_type':          SystemSetting.get('captcha_type', 'none'),
        'recaptcha_site_key':    SystemSetting.get('recaptcha_site_key', ''),
        'recaptcha_secret_key':  SystemSetting.get('recaptcha_secret_key', ''),
        'smtp_server':           SystemSetting.get('smtp_server', ''),
        'smtp_port':             SystemSetting.get('smtp_port', '587'),
        'smtp_sender_name':      SystemSetting.get('smtp_sender_name', 'TEXTQAI Support'),
        'smtp_user':             SystemSetting.get('smtp_user', ''),
        'smtp_password':         SystemSetting.get('smtp_password', ''),
        'active_ai_provider':    SystemSetting.get('active_ai_provider', 'openrouter'),
        'openrouter_api_key':    SystemSetting.get('openrouter_api_key', ''),
        'openai_api_key':        SystemSetting.get('openai_api_key', ''),
        'gemini_api_key':        SystemSetting.get('gemini_api_key', ''),
        'openrouter_model':      SystemSetting.get('openrouter_model', 'google/gemini-2.5-flash-lite'),
        'openai_model':          SystemSetting.get('openai_model', 'gpt-4o-mini'),
        'gemini_model':          SystemSetting.get('gemini_model', 'gemini-2.5-flash'),
        'google_client_id':      SystemSetting.get('google_client_id', ''),
        'google_client_secret':  SystemSetting.get('google_client_secret', ''),
        'google_redirect_uri':   SystemSetting.get('google_redirect_uri', ''),
        'vnpay_tmn_code':        SystemSetting.get('vnpay_tmn_code', ''),
        'vnpay_hash_secret':     SystemSetting.get('vnpay_hash_secret', ''),
        'vnpay_url':             SystemSetting.get('vnpay_url', 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html'),
        'vnpay_return_url':      SystemSetting.get('vnpay_return_url', ''),
        'sepay_api_key':         SystemSetting.get('sepay_api_key', ''),
        'secret_key':            SystemSetting.get('secret_key', ''),
        'has_secret_key':        bool(SystemSetting.get('secret_key', '').strip()),
    }
    return render_template('admin/settings.html', packages=packages, sub_packages=sub_packages, settings=settings)


# ── PUBLIC: nhận phản hồi từ landing page ─────────────────────────────────────
@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    data    = request.get_json(silent=True) or {}
    email   = (data.get('email') or '').strip()
    message = (data.get('message') or '').strip()
    if not email or not message:
        return {'ok': False, 'error': 'Thiếu thông tin'}, 400
    if len(email) > 255 or len(message) > 5000:
        return {'ok': False, 'error': 'Dữ liệu quá dài'}, 400
    user_id = current_user.id if current_user.is_authenticated else None
    fb = Feedback(email=email, message=message, user_id=user_id)
    db.session.add(fb)
    db.session.commit()
    return {'ok': True}, 201


# ── ADMIN: xem danh sách phản hồi ─────────────────────────────────────────────
@app.route('/admin/feedback')
@login_required
@admin_required
def admin_feedback():
    page     = request.args.get('page', 1, type=int)
    filter_r = request.args.get('read', '')          # '' | '0' | '1'
    query    = Feedback.query
    if filter_r == '0':
        query = query.filter_by(is_read=False)
    elif filter_r == '1':
        query = query.filter_by(is_read=True)
    feedbacks   = query.order_by(Feedback.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    unread_count = Feedback.query.filter_by(is_read=False).count()
    return render_template('admin/feedback.html',
                           feedbacks=feedbacks, filter_r=filter_r,
                           unread_count=unread_count)


@app.route('/admin/feedback/<int:fb_id>/read', methods=['POST'])
@login_required
@admin_required
def admin_feedback_read(fb_id):
    fb = Feedback.query.get_or_404(fb_id)
    fb.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for('admin_feedback'))


@app.route('/admin/feedback/<int:fb_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_feedback_delete(fb_id):
    fb = Feedback.query.get_or_404(fb_id)
    db.session.delete(fb)
    db.session.commit()
    flash('Đã xoá phản hồi.', 'success')
    return redirect(url_for('admin_feedback'))


# ── Legal / Store pages ───────────────────────────────────────────────────────
_LEGAL_UPDATED = '13/06/2026'

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', last_updated=_LEGAL_UPDATED)

@app.route('/terms')
def terms():
    return render_template('terms.html', last_updated=_LEGAL_UPDATED)

@app.route('/data-deletion')
def data_deletion():
    return render_template('data_deletion.html', last_updated=_LEGAL_UPDATED)

@app.route('/payment-policy')
def payment_policy():
    return render_template('payment_policy.html', last_updated=_LEGAL_UPDATED)

@app.route('/ai-policy')
def ai_policy():
    return render_template('ai_policy.html', last_updated=_LEGAL_UPDATED)

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon',
    )

@app.route('/user-guide')
def user_guide():
    return render_template('user_guide.html')


def _auto_cancel_pending_transactions():
    """Background thread: cứ 5 phút quét 1 lần, huỷ các giao dịch pending quá 30 phút."""
    while True:
        time.sleep(300)  # chạy mỗi 5 phút
        try:
            with app.app_context():
                cutoff = datetime.utcnow() - timedelta(minutes=30)
                expired = Transaction.query.filter(
                    Transaction.status == 'pending',
                    Transaction.created_at <= cutoff,
                ).all()
                if expired:
                    for txn in expired:
                        txn.status = 'cancelled'
                    db.session.commit()
                    print(f'[AUTO-CANCEL] Cancelled {len(expired)} pending transactions older than 30 mins.', flush=True)
        except Exception as e:
            print(f'[AUTO-CANCEL] Error: {e}', flush=True)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Chỉ tạo bảng nếu chưa có (không xóa dữ liệu)
        _apply_runtime_settings()
        from utils.db_schema import ensure_column
        try:
            ensure_column(db.engine, 'users', 'terms_agreed_at', 'terms_agreed_at TIMESTAMP NULL')
        except Exception:
            pass
    # Khởi động background thread tự huỷ pending transactions
    _cancel_thread = threading.Thread(target=_auto_cancel_pending_transactions, daemon=True)
    _cancel_thread.start()

    # Dùng Waitress (production WSGI, multi-threaded) nếu có,
    # fallback về Flask dev server khi dev local.
    try:
        from waitress import serve
        print(" * Running on http://0.0.0.0:5000 (Waitress - production mode)")
        serve(app, host='0.0.0.0', port=5000, threads=8)
    except ImportError:
        print(" * waitress chua cai, dung Flask dev server (chi dung khi dev).")
        app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
