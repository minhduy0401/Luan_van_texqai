"""Resolve danh sách PDF cho thí nghiệm — thư mục mặc định hoặc đường dẫn tùy ý."""
from __future__ import annotations

import argparse
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).parent.resolve()


def resolve_pdf_paths(
    paths: list[str] | None = None,
    pdf_dir: str | None = None,
    default_dir: Path | None = None,
) -> list[Path]:
    """Trả về danh sách PDF tuyệt đối, kiểm tra tồn tại."""
    if paths:
        out: list[Path] = []
        for raw in paths:
            pp = Path(raw).expanduser().resolve()
            if not pp.is_file():
                raise FileNotFoundError(f'Không tìm thấy PDF: {pp}')
            if pp.suffix.lower() != '.pdf':
                raise ValueError(f'Không phải file PDF: {pp}')
            out.append(pp)
        return out

    base = Path(pdf_dir).expanduser().resolve() if pdf_dir else (default_dir or EXPERIMENT_DIR)
    found = sorted(base.glob('*.pdf'))
    if not found:
        raise FileNotFoundError(
            f'Không tìm thấy PDF trong {base}.\n'
            '  • Copy giáo trình .pdf vào thư mục experiment/, hoặc\n'
            '  • Chạy với --pdf "C:\\duong\\dan\\giao_trinh.pdf", hoặc\n'
            '  • --pdf-dir "C:\\thu_muc\\chua_pdf"'
        )
    return found


def add_pdf_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--pdf', action='append', dest='pdfs', metavar='PATH',
        help='Đường dẫn PDF giáo trình (có thể chỉ định nhiều lần)',
    )
    parser.add_argument(
        '--pdf-dir', metavar='DIR',
        help='Thư mục chứa các file .pdf (mặc định: experiment/)',
    )


def pdfs_from_args(args) -> list[Path]:
    return resolve_pdf_paths(paths=getattr(args, 'pdfs', None), pdf_dir=getattr(args, 'pdf_dir', None))
