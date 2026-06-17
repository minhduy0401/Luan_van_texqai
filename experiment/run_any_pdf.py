"""Chạy pipeline sinh câu hỏi trên bất kỳ PDF giáo trình nào (smoke test nhanh)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

EXPERIMENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = EXPERIMENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.pdf_paths import add_pdf_cli, pdfs_from_args


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Sinh câu hỏi từ PDF giáo trình bất kỳ (không cần nằm trong experiment/)',
    )
    add_pdf_cli(parser)
    parser.add_argument('--bloom', type=int, default=3, choices=range(1, 7),
                        help='Mức Bloom (1–6), mặc định 3')
    parser.add_argument('--count', type=int, default=2, help='Số câu cần sinh')
    parser.add_argument('--points', type=float, default=1.5, help='Điểm mỗi câu')
    parser.add_argument('--ocr', action='store_true', help='Bật OCR khi đọc PDF')
    args = parser.parse_args()

    try:
        pdfs = pdfs_from_args(args)
    except (FileNotFoundError, ValueError) as e:
        print(f'❌ {e}')
        return 1

    pdf_path = pdfs[0]
    if len(pdfs) > 1:
        print(f'⚠️  Nhiều PDF — chỉ chạy file đầu: {pdf_path.name}')

    bloom_names = {
        1: 'Bloom 1 (Nhớ)', 2: 'Bloom 2 (Hiểu)', 3: 'Bloom 3 (Vận dụng)',
        4: 'Bloom 4 (Phân tích)', 5: 'Bloom 5 (Đánh giá)', 6: 'Bloom 6 (Sáng tạo)',
    }
    bloom_level = bloom_names[args.bloom]
    bloom_configs = [{'bloom_level': bloom_level, 'count': args.count, 'points': args.points}]

    from flask import Flask
    from extensions import db

    _db = EXPERIMENT_DIR / 'any_pdf_temp.db'
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'any-pdf-smoke'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{_db}?timeout=60'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    import config as _cfg
    from services.pdf import extract_pdf_text_plain, extract_pdf_text_with_ocr, split_document_into_sections
    from services.pipeline import run_agent_pipeline

    print(f"\n{'='*60}")
    print(f'  ANY-PDF SMOKE — {pdf_path.name}')
    print(f'  {bloom_level} × {args.count} câu | Model: {_cfg.QUESTION_MODEL}')
    print(f"{'='*60}\n")

    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        from experiment.experiment_runtime import seed_settings_from_main_app
        seed_settings_from_main_app(app)
        _cfg.sync_from_db()

        raw = pdf_path.read_bytes()
        if args.ocr:
            content, stats = extract_pdf_text_with_ocr(raw)
        else:
            content, stats = extract_pdf_text_plain(raw)

        if not content.strip():
            print('❌ Không trích xuất được nội dung — thử --ocr')
            return 1

        sections = split_document_into_sections(content, page_boundaries=stats.get('page_boundaries'))
        print(f'\n📄 Parse: {len(sections)} mục | {len(content):,} ký tự | {stats.get("total_pages", "?")} trang')

        t0 = time.time()
        results = run_agent_pipeline(
            content, stats, bloom_configs, args.count, 'new',
            user_id=1, document_id=1, progress_callback=None, ui_lang='vi',
        )
        elapsed = time.time() - t0

        ok = len(results)
        print(f'\n{"="*60}')
        print(f'  Kết quả: {ok}/{args.count} câu trong {elapsed:.0f}s')
        for i, r in enumerate(results, 1):
            print(f'\n--- Câu {i} ({r.get("bloom_level", "")}) ---')
            print(f'Q: {(r.get("question") or "")[:300]}')
            print(f'A: {(r.get("answer") or "")[:400]}...')
        print(f'{"="*60}\n')
        return 0 if ok >= 1 else 1


if __name__ == '__main__':
    raise SystemExit(main())
