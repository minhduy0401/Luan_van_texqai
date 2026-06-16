# services/pdf.py – PDF text extraction and document section detection
import pdfplumber
import io
import re
import os
import time
import random
import json
from collections import Counter

def clean_extracted_text(text):
    """Làm sạch text từ PDF: KHÔNG xử lý gì, giữ nguyên text gốc"""
    if not text:
        return ""
    
    # Chỉ loại bỏ khoảng trắng đầu/cuối dòng
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)
    
    return text.strip()

def _normalize_line_for_dedupe(text_line):
    """Chuẩn hóa dòng text để so trùng giữa extract text và OCR."""
    if not text_line:
        return ''
    normalized = re.sub(r'\W+', '', text_line.lower(), flags=re.UNICODE)
    return normalized.strip()


def _merge_extracted_and_ocr_text(extracted_text, ocr_text):
    """Gộp text thường và OCR, tránh lặp lại dòng giống nhau."""
    merged_lines = []
    seen = set()

    for source in [extracted_text or '', ocr_text or '']:
        for raw_line in source.splitlines():
            line = raw_line.strip()
            if len(line) < 2:
                continue
            key = _normalize_line_for_dedupe(line)
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            merged_lines.append(line)

    return '\n'.join(merged_lines).strip()


def _extract_page_pymupdf(fitz_page) -> str:
    """Trích text một trang bằng PyMuPDF (fitz) — tốt hơn pdfplumber với PDF LaTeX.
    Giữ lại ký hiệu toán học, chỉ số trên/dưới, chữ Hy Lạp.
    """
    try:
        # flags: preserve ligatures và ký hiệu đặc biệt
        text = fitz_page.get_text("text", flags=0)
        return (text or '').strip()
    except Exception as e:
        print(f"   [PyMuPDF] lỗi trang: {e}")
        return ''


def _count_stem_chars(text: str) -> int:
    """Đếm số ký tự STEM (toán/hóa) trong đoạn text để quyết định dùng PyMuPDF hay không."""
    stem_chars = 0
    for c in text:
        cp = ord(c)
        # Greek (α–ω, Α–Ω)
        if 0x0391 <= cp <= 0x03C9:
            stem_chars += 1
        # Math operators (∀, ∃, ∑, ∫, ∂, ∇, ∞...)
        elif 0x2200 <= cp <= 0x22FF:
            stem_chars += 1
        # Superscript/subscript (⁰–⁹, ₀–₉)
        elif 0x2070 <= cp <= 0x209F:
            stem_chars += 1
        # Common: ² ³ ± × ÷ °
        elif cp in (0x00B2, 0x00B3, 0x00B1, 0x00D7, 0x00F7, 0x00B0, 0x00B5):
            stem_chars += 1
    return stem_chars


def extract_pdf_text_plain(pdf_binary_data, page_callback=None):
    """Đọc PDF bằng text layer. Tự động dùng PyMuPDF cho trang có công thức STEM.
    page_callback(page_num, total_pages, label): gọi sau mỗi trang để cập nhật UI.
    Không chạy OCR — dùng extract_pdf_text_with_ocr() cho PDF scan.
    """
    if not pdf_binary_data:
        raise ValueError('PDF rỗng')

    # Thử import PyMuPDF (fitz)
    try:
        import fitz as _fitz
        fitz_doc = _fitz.open(stream=pdf_binary_data, filetype='pdf')
        has_pymupdf = True
    except ImportError:
        fitz_doc = None
        has_pymupdf = False
        print("   [INFO] PyMuPDF chưa cài — chỉ dùng pdfplumber. Cài: pip install pymupdf")

    content_parts = []
    page_boundaries = []  # [(char_offset, page_num), ...] to map text position → page
    stats = {
        'total_pages': 0,
        'pages_with_text_layer': 0,
        'pages_with_ocr_text': 0,
        'ocr_errors': 0,
        'pages_pymupdf': 0,
    }

    current_offset = 0
    with pdfplumber.open(io.BytesIO(pdf_binary_data)) as pdf:
        stats['total_pages'] = len(pdf.pages)
        print(f"   ├─ Tổng số trang: {stats['total_pages']} | PyMuPDF: {'✓' if has_pymupdf else '✗'}")

        for page_num, page in enumerate(pdf.pages, 1):
            page_text = (page.extract_text() or '').strip()
            if page_text:
                stats['pages_with_text_layer'] += 1

                # Kiểm tra trang có ký hiệu STEM không → nếu có, thử PyMuPDF
                stem_count = _count_stem_chars(page_text)

                # Phát hiện "broken words": avg word length quá ngắn
                # (e.g. "chap ter", "Licen se" → pdfplumber bị lỗi font encoding)
                words_on_page = page_text.split()
                avg_word_len = (sum(len(w) for w in words_on_page) / len(words_on_page)
                                if len(words_on_page) > 10 else 99)
                has_broken_words = avg_word_len < 4.5 and len(words_on_page) > 15

                if has_pymupdf and (stem_count >= 2 or has_broken_words):
                    try:
                        fitz_page = fitz_doc[page_num - 1]
                        fitz_text = _extract_page_pymupdf(fitz_page).strip()
                        if fitz_text:
                            fitz_words = fitz_text.split()
                            fitz_avg = (sum(len(w) for w in fitz_words) / len(fitz_words)
                                        if fitz_words else 0)
                            # Dùng PyMuPDF nếu: nhiều STEM hơn HOẶC avg word length cao hơn
                            use_fitz = (_count_stem_chars(fitz_text) > stem_count or
                                        (has_broken_words and fitz_avg > avg_word_len + 0.5))
                            if use_fitz:
                                page_text = fitz_text
                                stats['pages_pymupdf'] += 1
                                if has_broken_words and page_num <= 5:
                                    print(f"   [PyMuPDF] trang {page_num}: sửa broken words "
                                          f"(pdfplumber avg={avg_word_len:.1f} → fitz avg={fitz_avg:.1f})")
                    except Exception as e:
                        print(f"   [PyMuPDF] trang {page_num}: {e}")

                page_text = _normalize_pdf_text(page_text)
                page_boundaries.append((current_offset, page_num))
                content_parts.append(page_text)
                current_offset += len(page_text) + 2  # +2 for '\n\n' separator
            elif has_pymupdf:
                # pdfplumber không đọc được → thử PyMuPDF
                try:
                    fitz_page = fitz_doc[page_num - 1]
                    fitz_text = _extract_page_pymupdf(fitz_page).strip()
                    if fitz_text:
                        stats['pages_with_text_layer'] += 1
                        stats['pages_pymupdf'] += 1
                        fitz_text = _normalize_pdf_text(fitz_text)
                        page_boundaries.append((current_offset, page_num))
                        content_parts.append(fitz_text)
                        current_offset += len(fitz_text) + 2
                except Exception:
                    pass

            # Gọi callback tiến độ mỗi trang
            if page_callback:
                try:
                    label = f'pymupdf={stats["pages_pymupdf"]}' if stats['pages_pymupdf'] > 0 else ''
                    page_callback(page_num, stats['total_pages'], label)
                except Exception:
                    pass

            if page_num % 10 == 0 or page_num == stats['total_pages']:
                merged_chars = sum(len(p) for p in content_parts)
                print(f"   ├─ Đã đọc {page_num}/{stats['total_pages']} trang ({merged_chars:,} chars"
                      f" | pymupdf={stats['pages_pymupdf']})")

    if has_pymupdf and fitz_doc:
        fitz_doc.close()

    merged_content = '\n\n'.join(content_parts).strip()
    stats['page_boundaries'] = page_boundaries
    return merged_content, stats


_TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
_TESSERACT_AVAILABLE = None  # None = chưa kiểm tra

def _check_tesseract():
    """Kiểm tra Tesseract có sẵn và có ngôn ngữ vie không. Cache kết quả."""
    global _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is not None:
        return _TESSERACT_AVAILABLE
    import os
    if not os.path.isfile(_TESSERACT_CMD):
        print(f"   [OCR] Tesseract không tìm thấy tại {_TESSERACT_CMD}")
        _TESSERACT_AVAILABLE = False
        return False
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
        langs = pytesseract.get_languages()
        if 'vie' not in langs:
            print(f"   [OCR] Tesseract thiếu ngôn ngữ 'vie'. Có: {langs}")
            _TESSERACT_AVAILABLE = False
        else:
            print(f"   [OCR] Tesseract OK, ngôn ngữ: {langs}")
            _TESSERACT_AVAILABLE = True
    except Exception as e:
        print(f"   [OCR] Tesseract lỗi: {e}")
        _TESSERACT_AVAILABLE = False
    return _TESSERACT_AVAILABLE


def _preprocess_image_for_ocr(pil_image):
    """Tiền xử lý ảnh để OCR tốt hơn: grayscale → contrast → sharpen."""
    from PIL import ImageEnhance, ImageFilter
    gray = pil_image.convert('L')
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    gray = gray.filter(ImageFilter.SHARPEN)
    return gray  # Tesseract nhận ảnh grayscale trực tiếp


def _ocr_page_tesseract(pil_image):
    """OCR 1 trang bằng Tesseract (Vietnamese + English)."""
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    # --oem 3: LSTM engine, --psm 6: assume uniform block of text
    config = '--oem 3 --psm 6'
    text = pytesseract.image_to_string(pil_image, lang='vie+eng', config=config)
    return text.strip()


def _ocr_page_rapidocr(pil_image):
    """OCR 1 trang bằng RapidOCR (fallback khi Tesseract không có)."""
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    img_rgb = pil_image.convert('RGB')
    result, _ = engine(np.array(img_rgb))
    if not result:
        return ''
    lines = [str(item[1]).strip() for item in result if len(item) > 1 and item[1] and len(str(item[1]).strip()) >= 2]
    return '\n'.join(lines).strip()


# Ký tự STEM hợp lệ — KHÔNG được nhận nhầm là garbled
# Greek alphabet: α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω (và viết hoa)
# Toán học: ∑ ∫ ∂ ∇ ∞ ± × ÷ ≤ ≥ ≠ ≈ √ → ← ↔ ∈ ∉ ∀ ∃ ∅
# Chỉ số trên: ⁰ ¹ ² ³ ⁴ ⁵ ⁶ ⁷ ⁸ ⁹ ⁺ ⁻
# Chỉ số dưới: ₀ ₁ ₂ ₃ ₄ ₅ ₆ ₇ ₈ ₉ (H₂O, CO₂, Fe³⁺...)
# Ký hiệu vật lý: Å (angstrom), µ (micro), ° (degree)
_STEM_CHAR_RANGES = (
    (0x0391, 0x03C9),   # Greek: Α–ω (uppercase + lowercase)
    (0x2200, 0x22FF),   # Mathematical Operators block: ∀ ∃ ∅ ∇ ∈ ∉ ∏ ∑ ∗ ∞ ∫ ≤ ≥ ≠ ≈
    (0x2100, 0x214F),   # Letterlike Symbols: ℃ ℉ ℓ ℵ
    (0x2190, 0x21FF),   # Arrows: → ← ↑ ↓ ↔ ⇒ ⇔
    (0x2070, 0x209F),   # Superscript + Subscript: ⁰¹²³ ₀₁₂₃
    (0x00B0, 0x00B0),   # ° (degree sign)
    (0x00B1, 0x00B1),   # ± (plus-minus)
    (0x00D7, 0x00D7),   # × (multiplication sign)
    (0x00F7, 0x00F7),   # ÷ (division sign)
    (0x00B2, 0x00B3),   # ² ³ (superscript 2, 3 — rất phổ biến)
    (0x00B5, 0x00B5),   # µ (micro sign)
    (0x00C5, 0x00C5),   # Å (angstrom)
    (0x2260, 0x2265),   # ≠ ≡ ≤ ≥
    (0x221A, 0x221A),   # √ (square root)
    (0x0300, 0x036F),   # Combining diacritical marks (dùng trong IPA và một số ký hiệu KH)
)

def _is_stem_char(c):
    """Trả về True nếu ký tự thuộc tập ký hiệu STEM hợp lệ (không phải garbled)."""
    cp = ord(c)
    for lo, hi in _STEM_CHAR_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def _is_garbled_text(text):
    """Phát hiện text bị garbled do font cũ TCVN3/VNI.

    Nguyên lý:
    - Tiếng Việt Unicode THẬT: dấu thanh nằm ở U+1E00–U+1EFF
      (Latin Extended Additional: ắ ặ ổ ợ ẫ ẻ ẽ ụ ữ ấ ầ ẩ ẫ ậ ...)
    - TCVN3/VNI bị decode sai: bytes ra ký tự U+00C0–U+024F
      (Latin Extended A/B: ã â ä Ã Â Ä ï î Ç Þ...)
      nhưng KHÔNG có U+1E00–U+1EFF vì đây là encoding cũ 1-byte.
    - Ký hiệu STEM (α β ∑ ∫ H₂O CO₂): KHÔNG garbled — phải loại ra khỏi heuristic.

    Nếu text có nhiều non-ASCII nhưng gần như không có cả U+1E00–U+1EFF lẫn STEM → garbled.
    """
    if not text or len(text.strip()) < 20:
        return True

    total = len(text)
    non_ascii = sum(1 for c in text if ord(c) > 127)

    # Văn bản thuần ASCII (tiếng Anh, số, ký hiệu) → coi là đủ tin
    if non_ascii / total < 0.03:
        return False

    # Ký tự Vietnamese Unicode thật: U+1E00–U+1EFF
    viet_unicode = sum(1 for c in text if '\u1e00' <= c <= '\u1eff')

    # Ký tự STEM hợp lệ (α β γ ∑ ∫ ₂ ³ ...)
    stem_chars = sum(1 for c in text if ord(c) > 127 and _is_stem_char(c))

    # Nếu có non-ASCII đáng kể nhưng rất ít Vietnamese Unicode thật VÀ rất ít STEM
    # → text này là TCVN3/VNI garbled, không đáng tin
    if non_ascii >= 5:
        legit_ratio = (viet_unicode + stem_chars) / non_ascii
        if legit_ratio < 0.25:
            # Dưới 25% non-ASCII là ký tự hợp lệ → garbled
            return True

    return False


def extract_pdf_text_with_ocr(pdf_binary_data, page_callback=None):
    """Đọc PDF bằng OCR: dùng Tesseract (vie+eng) làm engine chính,
    RapidOCR làm fallback nếu Tesseract không có.
    page_callback(page_num, total_pages, label): gọi sau mỗi trang để cập nhật UI.
    Không dùng text layer garbled từ font cũ TCVN3/VNI.
    """
    if not pdf_binary_data:
        raise ValueError('PDF rỗng')

    use_tesseract = _check_tesseract()
    if use_tesseract:
        print("   [OCR] Dùng Tesseract (vie+eng) — chất lượng cao")
    else:
        print("   [OCR] Dùng RapidOCR (fallback) — chất lượng trung bình")
        # Kiểm tra RapidOCR
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa
        except ImportError as e:
            raise RuntimeError(f'Không có OCR engine nào: {e}')

    content_parts = []
    page_boundaries = []
    stats = {
        'total_pages': 0,
        'pages_with_text_layer': 0,
        'pages_with_ocr_text': 0,
        'ocr_errors': 0,
        'garbled_pages': 0,
    }

    current_offset = 0
    with pdfplumber.open(io.BytesIO(pdf_binary_data)) as pdf:
        stats['total_pages'] = len(pdf.pages)
        print(f"   ├─ Tổng số trang: {stats['total_pages']}")

        stats['pages_skipped_clean'] = 0

        for page_num, page in enumerate(pdf.pages, 1):
            text_layer = page.extract_text() or ''
            text_layer_has_content = bool(text_layer.strip())
            if text_layer_has_content:
                stats['pages_with_text_layer'] += 1

            garbled = _is_garbled_text(text_layer)
            if garbled and text_layer_has_content:
                stats['garbled_pages'] += 1

            # ── Phương án 1: Bỏ qua OCR nếu text layer đã sạch ──────────────
            # Trang có đủ từ Unicode tiếng Việt/Latin → không cần scan ảnh
            _word_count = len(text_layer.split())
            if text_layer_has_content and not garbled and _word_count >= 30:
                # Text layer đủ tốt → dùng luôn, bỏ qua OCR hoàn toàn
                page_text = text_layer
                src_label = 'text-layer(skip-ocr)'
                stats['pages_skipped_clean'] += 1
                ocr_words = 0
                layer_words = _word_count
                if page_num <= 5 or page_num % 20 == 0 or page_num == stats['total_pages']:
                    print(f"   p{page_num:03d}: layer={layer_words}w → [{src_label}] ✓ bỏ qua OCR")
                if page_text:
                    page_text = _normalize_pdf_text(page_text)
                    page_boundaries.append((current_offset, page_num))
                    content_parts.append(page_text)
                    current_offset += len(page_text) + 2
                # Gọi callback cho trang skip-OCR
                if page_callback:
                    try:
                        page_callback(page_num, stats['total_pages'], 'text')
                    except Exception:
                        pass
                continue  # sang trang tiếp theo, không chạy OCR

            # ── Chạy OCR: trang garbled, trang trắng, hoặc text quá ít ──────
            ocr_text = ''
            ocr_error_msg = ''
            try:
                raw_img = page.to_image(resolution=250).original
                processed_img = _preprocess_image_for_ocr(raw_img)

                if use_tesseract:
                    ocr_text = _ocr_page_tesseract(processed_img)
                else:
                    ocr_text = _ocr_page_rapidocr(processed_img)

                if ocr_text:
                    stats['pages_with_ocr_text'] += 1
            except Exception as exc:
                stats['ocr_errors'] += 1
                ocr_error_msg = str(exc)

            # Chọn nguồn text: OCR > text layer sạch > bỏ qua (nếu garbled + OCR fail)
            if ocr_text:
                page_text = ocr_text
                src_label = 'Tesseract' if use_tesseract else 'RapidOCR'
            elif text_layer_has_content and not garbled:
                page_text = text_layer
                src_label = 'text-layer(fallback)'
            elif text_layer_has_content and garbled:
                page_text = ''
                src_label = 'SKIP(garbled+ocr-fail)'
            else:
                page_text = ''
                src_label = 'EMPTY'

            ocr_words = len(ocr_text.split()) if ocr_text else 0
            layer_words = len(text_layer.split()) if text_layer else 0
            garbled_flag = '⚠garbled' if garbled else ''
            if page_num <= 5 or page_num % 20 == 0 or page_num == stats['total_pages']:
                print(f"   p{page_num:03d}: layer={layer_words}w {garbled_flag} | ocr={ocr_words}w → [{src_label}]"
                      + (f" ERR:{ocr_error_msg[:60]}" if ocr_error_msg else ''))

            if page_text:
                page_text = _normalize_pdf_text(page_text)
                page_boundaries.append((current_offset, page_num))
                content_parts.append(page_text)
                current_offset += len(page_text) + 2

            # Gọi callback tiến độ sau mỗi trang OCR
            if page_callback:
                try:
                    page_callback(page_num, stats['total_pages'], 'OCR')
                except Exception:
                    pass

        total_chars = sum(len(p) for p in content_parts)
        skipped = stats.get('pages_skipped_clean', 0)
        print(f"   └─ Kết quả: {len(content_parts)} trang | {total_chars:,} chars | "
              f"skip_clean={skipped} | garbled={stats['garbled_pages']} | "
              f"ocr_ok={stats['pages_with_ocr_text']} | err={stats['ocr_errors']}")

    merged_content = '\n\n'.join(content_parts).strip()
    stats['page_boundaries'] = page_boundaries
    return merged_content, stats


def detect_strict_section_headers(text, min_count=2):
    """Phát hiện tài liệu có chỉ mục thật dựa trên header dạng x.y ở đầu dòng."""
    if not text:
        return False, 0

    count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Chỉ tính header section khi số mục ở đầu dòng và có tiêu đề theo sau.
        if re.match(r'^\d+\.\d+(?:\.\d+)*\s+\S+', line):
            count += 1

    return count >= min_count, count

def extract_section_number(title):
    """Trích xuất số phần thực từ title (ví dụ: 'Phần II', 'Chương 3', '2.2.3', '1.4.1', '5.1.2')"""
    if not title:
        return None
    
    # Làm sạch cơ bản
    title_clean = re.sub(r'\s+', ' ', title).strip()
    # Gộp "1. 4. 1" -> "1.4.1" và "5 . 1 . 2" -> "5.1.2"
    for _ in range(5):  # Tăng lên 5 lần để xử lý số dài hơn
        title_clean = re.sub(r'(\d+)\.\s+(\d+)', r'\1.\2', title_clean)
    
    # Ưu tiên CAO NHẤT: Số có dấu chấm nhiều cấp (4-5 cấp)
    match = re.match(r'^(\d+\.\d+\.\d+\.\d+(?:\.\d+)?)\s+', title_clean)  # 4-5 cấp: 5.1.2.1, 1.2.3.4.5
    if match:
        return match.group(1)
    
    match = re.match(r'^(\d+\.\d+\.\d+)\s+', title_clean)  # 3 cấp: 5.1.2, 1.4.1
    if match:
        return match.group(1)
    
    match = re.match(r'^(\d+\.\d+)\s+', title_clean)  # 2 cấp: 2.2, 8.3
    if match:
        return match.group(1)
    
    # Nếu không tìm thấy ở đầu, thử tìm trong 50 ký tự đầu (trường hợp có ký tự lạ phía trước)
    first_part = title_clean[:50]
    match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)\s+', first_part)  # 3-4 cấp
    if match:
        return match.group(1)
    
    match = re.search(r'(\d+\.\d+)\s+', first_part)  # 2 cấp
    if match:
        return match.group(1)
    
    # Pattern: "Phần II", "Phần 2", "PHAN II"
    match = re.match(r'^(Ph\s*ần|PHAN|phần)\s+([IVXivx]+|\d+)', title_clean, re.IGNORECASE)
    if match:
        return f"Phần {match.group(2).upper()}"
    
    # Pattern: "Chương 3", "CHUONG 5"
    match = re.match(r'^(Ch\s*ương|CHUONG|chương)\s+(\d+)', title_clean, re.IGNORECASE)
    if match:
        return f"Chương {match.group(2)}"
    
    # Pattern: "Mục 2", "Mục 3.1", "MỤC 5.1.2"
    match = re.match(r'^(Mục|MUC|mục)\s+(\d+(?:\.\d+)*)', title_clean, re.IGNORECASE)
    if match:
        return f"Mục {match.group(2)}"
    
    # Pattern: Số đơn + space + chữ (ví dụ: "16 Tên mục")
    match = re.match(r'^(\d+)\s+[a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵA-Z]', title_clean, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

def clean_section_title(title):
    """Làm sạch tiêu đề section: chỉ gộp chữ bị tách rời, KHÔNG tách chữ dính"""
    if not title:
        return ""
    
    # GỘP chữ bị tách rời - lặp nhiều lần
    for _ in range(6):
        # Pattern đặc biệt 1: "lư ợng", "mư ợn", "tư ợng" -> "lượng", "mượn", "tượng"
        title = re.sub(
            r'([a-zđ][ươ]) ([ợơ][a-zngmtc]*)',
            r'\1\2',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern đặc biệt 2: "dử ông", "nử ớc" -> "dướng", "nước"
        title = re.sub(
            r'([a-zđ][ửữự]) ([ôơộồốớờở][a-zngmtc]*)',
            r'\1\2',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern đặc biệt 3: "kh ả n", "tá c d" -> "khản", "tác d"
        # á/ả/ã + space + phụ âm
        title = re.sub(
            r'([a-zđ][áảãạ]) ([bcdđghklmnpqrstvx])',
            r'\1\2',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern đặc biệt 4: "d ụng", "n ăng" -> "dụng", "năng"
        # CHỈ gộp khi ký tự TRƯỚC là chữ (không phải space) + space + ụ/ă/ê/ô
        title = re.sub(
            r'([a-zđ]) ([ụăêô][a-zngmtc]+)\b',
            r'\1\2',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern 1: chữ + space + 1-2 ký tự CÓ DẤU
        title = re.sub(
            r'([a-zđ]) ([àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]?)\b',
            r'\1\2',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: chữ + space + 1 ký tự có dấu đơn + space/dấu câu/cuối
        title = re.sub(
            r'([a-zđ]) ([àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ])(\s|[,.\-:;()]|$)',
            r'\1\2\3',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern 3: ký tự có dấu + space + 1 chữ + ký tự có dấu
        title = re.sub(
            r'([àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]) ([a-zđ][àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ])',
            r'\1\2',
            title,
            flags=re.IGNORECASE
        )
    
    # TÁCH chữ dính nhau - CHỈ các pattern cụ thể
    # Pattern 1: Cuối từ (ử/ữ/ự/ộ/ọ/ồ/ộ) + 'd' hoặc 'đ' + nguyên âm có dấu → tách "tửdá" → "tử đá"
    title = re.sub(
        r'([ửữựộọồốờởỡợ])([dđ][àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ])',
        r'\1 \2',
        title,
        flags=re.IGNORECASE
    )
    
    # Pattern 2: Từ phổ biến kết thúc bằng nguyên âm có dấu + 'ch' + nguyên âm → "chinhthức" → "chính thức"
    title = re.sub(
        r'([àáảãạíỉĩịúủũụ])(ch[ìíỉĩịoòóỏõọ])',
        r'\1 \2',
        title,
        flags=re.IGNORECASE
    )
    
    # Pattern 3: Cuối từ + 't' + nguyên âm có dấu (h/th phía sau) → "đấtth" → "đất th", "nhấtth" → "nhất th"
    title = re.sub(
        r'([ấậếệốộớợứự])(th?[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựửữựỳýỷỹỵ])',
        r'\1 \2',
        title,
        flags=re.IGNORECASE
    )
    
    # Pattern 4: "và/bảo/đảm/cho" + phụ âm + nguyên âm → "vàđảm" → "và đảm", "chothiết" → "cho thiết"
    title = re.sub(
        r'\b(và|bảo|đảm|cho|của|các|một|được)([bcdđghklmnpqrstvx][aàáảãạăắằẳẵặâấầẩẫậeèéẻẽẹêếềểễệiìíỉĩịoòóỏõọôốồổỗộơớờởỡợuùúủũụưứừửữựyỳýỷỹỵ])',
        r'\1 \2',
        title,
        flags=re.IGNORECASE
    )
    
    # Pattern 5: Phụ âm + nguyên âm + 'n/ng/nh/m/t/p/c/ch' (cuối từ) + phụ âm + nguyên âm → "nhânhượng" → "nhân hượng"
    title = re.sub(
        r'([a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][nmp])([bcdđghklmnpqrstvx][aàáảãạăắằẳẵặâấầẩẫậeèéẻẽẹêếềểễệiìíỉĩịoòóỏõọôốồổỗộơớờởỡợuùúủũụưứừửữựyỳýỷỹỵ])',
        r'\1 \2',
        title,
        flags=re.IGNORECASE
    )
    
    # Pattern 6: Chữ thường/có dấu + CHỮ HOA → "BộCông" → "Bộ Công", "thươngThống" → "thương Thống"
    title = re.sub(
        r'([a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ])([A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ])',
        r'\1 \2',
        title
    )
    
    # Pattern 7: Các từ phổ biến dính nhau - xử lý từng cặp cụ thể
    common_pairs = [
        (r'\b(thông)(báo)', r'\1 \2'),       # thôngbáo → thông báo
        (r'\b(công)(cụ)', r'\1 \2'),         # côngcụ → công cụ  
        (r'\b(cổng)(cụ)', r'\1 \2'),         # cổngcụ → cổng cụ
        (r'\b(qua)(cổng)', r'\1 \2'),        # quacổng → qua cổng
        (r'\b(trực)(tuyến)', r'\1 \2'),      # trựctuyến → trực tuyến
        (r'\b(điện)(tử)', r'\1 \2'),         # điệntử → điện tử
        (r'\b(doanh)(nghiệp)', r'\1 \2'),    # doanhnghiệp → doanh nghiệp
        (r'\b(thực)(phẩm)', r'\1 \2'),       # thựcphẩm → thực phẩm
        (r'\b(chức)(năng)', r'\1 \2'),       # chứcnăng → chức năng
        (r'\b(hiện)(hành)', r'\1 \2'),       # hiệnhành → hiện hành
        (r'\b(quy)(định)', r'\1 \2'),        # quyđịnh → quy định
        (r'\b(theo)(quy)', r'\1 \2'),        # theoquy → theo quy
        (r'\b(từ)(một)', r'\1 \2'),          # từmột → từ một
        (r'\b(trở)(đến)', r'\1 \2'),         # trởđến → trở đến
        (r'\b(khác)(trở)', r'\1 \2'),        # kháctrở → khác trở
        (r'\b(website)(khác)', r'\1 \2'),    # websitekhác → website khác
        (r'\b(liên)(kết)', r'\1 \2'),        # liênkết → liên kết
        (r'\b(những)(liên)', r'\1 \2'),      # nhữngliên → những liên
        (r'\b(là)(những)', r'\1 \2'),        # lànhững → là những
        (r'\b(chính)(là)', r'\1 \2'),        # chínhlà → chính là
        (r'\b(backlink)(chính)', r'\1 \2'),  # backlinkchính → backlink chính
        (r'\b(chất)(lượng)', r'\1 \2'),      # chấtlượng → chất lượng
        (r'\b(số)(lượng)', r'\1 \2'),        # sốlượng → số lượng
        (r'\b(ảnh)(hưởng)', r'\1 \2'),       # ảnhhưởng → ảnh hưởng
        (r'\b(thứ)(hạng)', r'\1 \2'),        # thứhạng → thứ hạng
        (r'\b(từ)(khóa)', r'\1 \2'),         # từkhóa → từ khóa
        (r'\b(tìm)(kiếm)', r'\1 \2'),        # tìmkiếm → tìm kiếm
        (r'\b(quan)(điểm)', r'\1 \2'),       # quandiểm → quan điểm
        (r'\b(được)(coi)', r'\1 \2'),        # đượccoi → được coi
        (r'\b(hợp)(lệ)', r'\1 \2'),          # hợplệ → hợp lệ
    ]
    
    for pattern, replacement in common_pairs:
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    
    # Pattern 8: Tách chữ dính tổng quát - nguyên âm có dấu + phụ âm (không có space)
    # "từmột" → "từ một", "trởđến" → "trở đến"
    title = re.sub(
        r'([ơưôơờớởỡợ])([mđtcklnhbpgvs][àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ])',
        r'\1 \2',
        title,
        flags=re.IGNORECASE
    )
    
    # Loại bỏ nhiều space (2+) thành 1
    title = re.sub(r'  +', ' ', title)
    
    return title.strip()

def _truncate_title_safely(title, max_length=80):
    """Cắt tiêu đề an toàn, không cắt giữa từ"""
    title = title.strip()
    
    # Làm sạch title - chỉ xử lý các ký tự bị tách rời
    title = clean_section_title(title)
    
    # Nếu đủ ngắn, giữ nguyên
    if len(title) <= max_length:
        return title
    
    # Cắt tại max_length, tìm khoảng trắng gần nhất để không cắt giữa từ
    truncated = title[:max_length]
    
    # Tìm vị trí khoảng trắng cuối cùng
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.7:  # Nếu khoảng trắng ở 70% cuối thì ok
        return truncated[:last_space].strip()
    else:
        # Nếu không có khoảng trắng phù hợp, cắt tại max_length
        return truncated.strip()

def _normalize_pdf_text(text):
    """
    Normalize PDF‑extracted text and preserve chemical/math formulas.

    - Convert non‑breaking spaces to normal spaces.
    - Remove zero‑width characters (while keeping sub/superscript ranges).
    - Translate Unicode subscript/superscript digits and symbols into HTML
      <sub>...</sub> and <sup>...</sup> tags so the frontend renders them correctly.
    - Collapse multiple spaces while preserving line breaks.
    """
    # 1. Basic whitespace cleanup
    text = text.replace('\u00a0', ' ')  # non‑breaking space → normal space

    # 2. Strip zero‑width characters that are not part of formula ranges
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    text = text.replace('\ufeff', '')   # BOM

    # 3. Maps for Unicode subscripts and superscripts
    sub_map = {
        '\u2080': '0', '\u2081': '1', '\u2082': '2', '\u2083': '3', '\u2084': '4',
        '\u2085': '5', '\u2086': '6', '\u2087': '7', '\u2088': '8', '\u2089': '9',
        '\u208a': '+', '\u208b': '-', '\u208c': '=', '\u208d': '(', '\u208e': ')',
    }
    sup_map = {
        '\u2070': '0', '\u00b9': '1', '\u00b2': '2', '\u00b3': '3', '\u2074': '4',
        '\u2075': '5', '\u2076': '6', '\u2077': '7', '\u2078': '8', '\u2079': '9',
        '\u207a': '+', '\u207b': '-', '\u207c': '=', '\u207d': '(', '\u207e': ')',
        '\u207f': 'n',
    }

    # 4. Replace each subscript with <sub>…</sub>
    for uni, val in sub_map.items():
        text = text.replace(uni, f'<sub>{val}</sub>')

    # 5. Replace each superscript with <sup>…</sup>
    for uni, val in sup_map.items():
        text = text.replace(uni, f'<sup>{val}</sup>')

    # 6. Collapse multiple spaces (preserve newlines)
    text = re.sub(r'[^\S\n]+', ' ', text)
    return text


def _lookup_page_number(char_offset, page_boundaries):
    """Given a character offset in the merged text, find the PDF page number.
    page_boundaries: list of (start_offset, page_num) sorted by start_offset.
    Returns page_num (int) or None."""
    if not page_boundaries:
        return None
    # Binary search for the last boundary <= char_offset
    result_page = page_boundaries[0][1]
    for start, page_num in page_boundaries:
        if start <= char_offset:
            result_page = page_num
        else:
            break
    return result_page


def split_document_into_sections(text, page_boundaries=None):
    """Chia tài liệu thành các sections/mục cụ thể với nội dung đầy đủ
    page_boundaries: optional list of (char_offset, page_num) from PDF extraction"""
    # CRITICAL: Normalize PDF text first (non-breaking spaces, etc.)
    text = _normalize_pdf_text(text)
    
    print(f"\n🔍 Bắt đầu parse document ({len(text):,} chars, {len(text.split()):,} words)")
    
    # DEBUG: Show first occurrence of potential headers
    bai_inline = re.search(r'(Bài|BÀI|bài)\s+\d+[.:)\s]', text)
    if bai_inline:
        ctx_start = max(0, bai_inline.start() - 20)
        ctx_end = min(len(text), bai_inline.end() + 60)
        print(f"  📌 First 'Bài' found at pos {bai_inline.start()}: ...{repr(text[ctx_start:ctx_end])}...")
    else:
        print(f"  📌 No 'Bài' pattern found in text")
    
    lines = text.split('\n')
    sections = []
    
    # Patterns để nhận diện tiêu đề chương/mục — bao gồm cả tài liệu STEM
    header_patterns = [
        r'^\d+\.\d+\.\d+(?:\.\d+)?\s+',  # 5.1.2, 1.4.1, 2.3.4.5 (3-4 cấp)
        r'^\d+\.\d+\s+',  # 2.2, 8.3 (2 cấp) - ƯU TIÊN CAO NHẤT
        r'^(Chương|CHƯƠNG|CHUONG|Chuong)\s+[IVX\d]+[:\.\s]',  # CHƯƠNG I, Chương 1
        r'^(Mục|MỤC|MUC)\s+[\d\.]+[:\.\s]',  # MỤC 1.1, Mục 2.3
        r'^(Phần|PHẦN|PHAN)\s+[IVX\d]+[:\.\s]',  # PHẦN I, Phần II
        r'^(Bài|BÀI|Bai|BAI|bài)\s+\d+[.:;)\s]',  # Bài 1. , BÀI 2: , Bài 3) etc
        r'^(Lesson|LESSON)\s+\d+[.:;)\s]',  # Lesson 1. , LESSON 2:
        r'^(Chapter|CHAPTER|Chap)\s+[IVX\d]+[:\.\s]',  # Chapter 1, CHAPTER 2 (English)
        # ── STEM-specific headers ─────────────────────────────────────────────
        r'^(Ví dụ|VÍ DỤ|Vi du|Example|EXAMPLE)\s+[\d.]+[.:)\s]',  # Ví dụ 3.1, Example 2
        r'^(Bài tập|BÀI TẬP|Exercise|EXERCISE)\s+[\d.]+',  # Bài tập 2.1, Exercise 3
        r'^(Định lý|ĐỊNH LÝ|Theorem|THEOREM)\s+[\d.]+',    # Định lý 2, Theorem 3.1
        r'^(Hệ quả|Corollary|Lemma|LEMMA)\s+[\d.]+',       # Hệ quả 1, Corollary 2
        r'^(Định nghĩa|ĐỊNH NGHĨA|Definition|DEF)\s+[\d.]+', # Định nghĩa 4, Definition 1
        r'^(Mệnh đề|Proposition|PROPOSITION)\s+[\d.]+',     # Mệnh đề 3
        r'^(Chứng minh|Proof)[.:?]?\s*$',                   # Chứng minh: (standalone)
        r'^(Nhận xét|Chú ý|Remark|NOTE|Note)\s+[\d.]+',    # Nhận xét 1, Remark 2
        r'^(Thuật toán|Algorithm|ALGORITHM)\s+[\d.]+',      # Thuật toán 3, Algorithm 1
        r'^(Phản ứng|Reaction)\s+[\d.]+[.:)\s]',           # Phản ứng 2.1 (hóa học)
    ]
    
    current_section = None
    current_content = []
    current_chapter = None  # Track Phần hiện tại (Phần I, Phần II, ...)
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Kiểm tra xem có phải tiêu đề mục không
        is_header = False
        for pattern in header_patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                is_header = True
                break
        
        # THÊM KIỂM TRA: Chỉ chấp nhận header nếu BẮT ĐẦU bằng SỐ hoặc keyword
        valid_start = (
            re.match(r'^\d+\.', line_stripped) or  # Bắt đầu bằng số (1.1, 2.3)
            re.match(r'^(Chương|CHƯƠNG|Mục|MỤC|Phần|PHẦN)', line_stripped, re.IGNORECASE) or
            re.match(r'^(Bài|BÀI|Bai|BAI|Lesson|LESSON|Chapter|CHAPTER|Chap)\s+\d+', line_stripped, re.IGNORECASE)
        )
        
        if is_header and valid_start and len(line_stripped) > 3 and len(line_stripped) < 200:
            # CRITICAL FIX: Lưu section cũ TRƯỚC KHI cập nhật chapter
            # (vì chapter mới sẽ được dùng cho section mới, không phải section cũ)
            if current_section and current_content:
                content_text = '\n'.join(current_content).strip()
                # Chỉ lưu section có nội dung đủ dài (>100 ký tự)
                if len(content_text) > 100:
                    sections.append({
                        'chapter': current_chapter,  # Dùng chapter của section cũ
                        'title': current_section,
                        'content': content_text,
                        'word_count': len(content_text.split()),
                        'char_count': len(content_text)
                    })
            
            # BÂY GIỜ cập nhật chapter từ header mới
            # QUAN TRỌNG: Extract chapter từ số section (2.1 → Chương 2)
            section_num_match = re.match(r'^(\d+)\.', line_stripped)
            if section_num_match:
                chapter_num = section_num_match.group(1)
                current_chapter = f"Chương {chapter_num}"
                # DEBUG: Track chapters > 2
                if int(chapter_num) > 2:
                    print(f"  🔍 Found Chương {chapter_num}: {line_stripped[:80]}")
            
            # Kiểm tra xem có phải tiêu đề Phần/Chương không (override nếu có)
            chapter_match = re.match(r'^(Phần|PHAN|phần|Chương|CHUONG)\s+([IVXivx]+|\d+)', line_stripped, re.IGNORECASE)
            if chapter_match:
                roman_or_num = chapter_match.group(2).upper()
                print(f"  🔍 Found chapter header: {line_stripped[:80]} (raw: {roman_or_num})")
                # Convert La Mã sang số (ĐẦY ĐỦ I-XXX = 1-30)
                roman_map = {
                    'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5',
                    'VI': '6', 'VII': '7', 'VIII': '8', 'IX': '9', 'X': '10',
                    'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15',
                    'XVI': '16', 'XVII': '17', 'XVIII': '18', 'XIX': '19', 'XX': '20',
                    'XXI': '21', 'XXII': '22', 'XXIII': '23', 'XXIV': '24', 'XXV': '25',
                    'XXVI': '26', 'XXVII': '27', 'XXVIII': '28', 'XXIX': '29', 'XXX': '30'
                }
                
                if roman_or_num in roman_map:
                    current_chapter = f"Chương {roman_map[roman_or_num]}"
                else:
                    # Nếu không phải La Mã hoặc là số Ả Rập, dùng trực tiếp
                    current_chapter = f"Chương {roman_or_num}"
            
            # Kiểm tra "Chapter X" tiếng Anh → group as Chapter
            chapter_en_match = re.match(r'^(Chapter|CHAPTER|Chap)\s+([IVX\d]+)[:\.\s]\s*(.*)', line_stripped, re.IGNORECASE)
            if chapter_en_match:
                chap_num = chapter_en_match.group(2).strip()
                chap_topic = chapter_en_match.group(3).strip().rstrip('.').strip()
                # Convert Roman numerals if needed
                roman_map = {'I':'1','II':'2','III':'3','IV':'4','V':'5','VI':'6',
                             'VII':'7','VIII':'8','IX':'9','X':'10','XI':'11','XII':'12'}
                chap_num_str = roman_map.get(chap_num.upper(), chap_num)
                if chap_topic:
                    current_chapter = f"Chapter {chap_num_str}: {chap_topic[:50]}"
                else:
                    current_chapter = f"Chapter {chap_num_str}"
                print(f"  🔍 Found English Chapter {chap_num_str}: {chap_topic[:60]} → chapter='{current_chapter[:50]}'")

            # Kiểm tra "Bài X. Title" → group by topic title as pseudo-chapter
            bai_match = re.match(r'^(Bài|BÀI|Bai|BAI|bài|Lesson|LESSON)\s+(\d+)[.:;)\s]\s*(.*)', line_stripped, re.IGNORECASE)
            if bai_match:
                bai_num = int(bai_match.group(2))
                bai_topic = bai_match.group(3).strip().rstrip('.').strip()
                if bai_topic:
                    # Use topic name as chapter (e.g. "Khái niệm cơ sở dữ liệu")
                    current_chapter = f"Chủ đề: {bai_topic}"
                else:
                    current_chapter = f"Bài {bai_num}"
                print(f"  🔍 Found Bài {bai_num}: {bai_topic[:60]} → chapter='{current_chapter[:50]}'")
            
            # Bắt đầu section mới - CHỈ LẤY TIÊU ĐỀ THẬT (không lấy content)
            title_clean = line_stripped
            # Chỉ loại bỏ nhiều khoảng trắng (2+ spaces) thành 1 space
            title_clean = re.sub(r'  +', ' ', title_clean)
            
            # CRITICAL: Giới hạn title nghiêm ngặt hơn - CHỈ 1 DÒNG!
            # Nếu có xuống dòng trong title → chỉ lấy dòng đầu
            if '\n' in title_clean:
                title_clean = title_clean.split('\n')[0].strip()
            
            # Giới hạn độ dài title - max 150 chars (tiêu đề thật thường <100 chars)
            if len(title_clean) > 150:
                # Tìm dấu chấm, dấu hai chấm đầu tiên (thường kết thúc tiêu đề)
                punct_pos = min(
                    title_clean.find('.', 50) if title_clean.find('.', 50) > 0 else 999,
                    title_clean.find(':', 50) if title_clean.find(':', 50) > 0 else 999
                )
                if punct_pos < 150:
                    title_clean = title_clean[:punct_pos].strip()
                else:
                    # Cắt tại khoảng trắng gần 100 chars
                    last_space = title_clean[:100].rfind(' ')
                    if last_space > 50:
                        title_clean = title_clean[:last_space]
                    else:
                        title_clean = title_clean[:100]
            
            current_section = title_clean
            current_content = []
        else:
            # Thêm nội dung vào section hiện tại
            if line_stripped:  # Bỏ dòng trống
                current_content.append(line_stripped)
    
    # Lưu section cuối cùng
    if current_section and current_content:
        content_text = '\n'.join(current_content).strip()
        if len(content_text) > 100:
            sections.append({
                'chapter': current_chapter,  # Thêm Phần hiện tại
                'title': current_section,
                'content': content_text,
                'word_count': len(content_text.split()),
                'char_count': len(content_text)
            })
    
    # Nếu không tìm thấy sections rõ ràng → thử detect "Bài X." inline (PDF often merges lines)
    if len(sections) == 0:
        print(f"  ⚠️ Primary parse found 0 sections. Trying inline 'Bài X.' detection...")
        
        # Try to find "Bài X." patterns WITHIN the text (not just at line start)
        bai_pattern = re.compile(r'(Bài|BÀI|bài)\s+(\d+)[.:;)\s]\s*([^\n]{3,80})', re.IGNORECASE)
        bai_matches = list(bai_pattern.finditer(text))
        
        if bai_matches:
            print(f"  ✅ Found {len(bai_matches)} 'Bài X.' patterns inline!")
            topic_map = {}  # {topic: chapter_name}
            
            for idx, match in enumerate(bai_matches):
                bai_num = int(match.group(2))
                bai_topic = match.group(3).strip().rstrip('.').strip()
                start_pos = match.start()
                
                # Content = from after this match to next match (or end)
                end_pos = bai_matches[idx + 1].start() if idx + 1 < len(bai_matches) else len(text)
                content_text = text[start_pos:end_pos].strip()
                
                # Remove the "—" separator if present
                content_text = re.sub(r'\n—\s*$', '', content_text).strip()
                
                # Determine chapter by topic
                if bai_topic not in topic_map:
                    topic_map[bai_topic] = f"Chủ đề: {bai_topic}"
                chapter = topic_map[bai_topic]
                
                title = f"Bài {bai_num}. {bai_topic}"
                
                if len(content_text) > 50:
                    sections.append({
                        'chapter': chapter,
                        'title': title,
                        'content': content_text,
                        'word_count': len(content_text.split()),
                        'char_count': len(content_text),
                    })
            
            print(f"  ✅ Inline detection: {len(sections)} sections from {len(topic_map)} topics")
    
    # STILL no sections → thử tách đoạn đánh số "1.", "2.", "3."...
    if len(sections) == 0:
        print(f"  ⚠️ No sections detected. Trying numbered-paragraph detection (1. 2. 3. ...)...")
        num_pattern = re.compile(
            r'(?:^|\n)(\d{1,3})\.\s*\n?[\u201c"\'](.+?)[\u201d"\']\s*(?=\n\d{1,3}\.\s|\Z)',
            re.DOTALL
        )
        num_matches = list(num_pattern.finditer(text))
        if not num_matches:
            # Fallback pattern: đoạn bắt đầu bằng số. và nội dung tự do (không có quote)
            num_pattern2 = re.compile(r'(?:^|\n)(\d{1,3})\.\s*\n(.+?)(?=\n\d{1,3}\.\s|\Z)', re.DOTALL)
            num_matches = list(num_pattern2.finditer(text))

        if num_matches:
            print(f"  ✅ Found {len(num_matches)} numbered paragraphs!")
            seen_nums = set()
            for idx, m in enumerate(num_matches):
                num = int(m.group(1))
                if num in seen_nums:
                    continue
                seen_nums.add(num)
                content_text = re.sub(r'\s+', ' ', m.group(2)).strip()
                # Strip nhãn [Bloom X ...] nếu có (file có nhãn)
                content_text = re.sub(r'\s*\[Bloom\s*\d+[^\]]*\]\s*$', '', content_text).strip()
                if len(content_text) > 50:
                    sections.append({
                        'chapter': f'Đoạn {num}',
                        'title': f'Đoạn {num}: {content_text[:60]}...' if len(content_text) > 60 else f'Đoạn {num}: {content_text}',
                        'content': content_text,
                        'word_count': len(content_text.split()),
                        'char_count': len(content_text),
                    })
            print(f"  ✅ Numbered-paragraph: {len(sections)} sections")

    # STILL no sections → fallback to paragraph chunks
    if len(sections) == 0:
        print(f"  ⚠️ No sections detected at all. Falling back to paragraph chunks...")

        if page_boundaries and len(page_boundaries) > 1:
            # === PAGE-BOUNDARY-AWARE CHUNKING ===
            # Group consecutive pages into chunks of ~2000 chars, respecting exact page boundaries
            print(f"  📄 Chunking theo ranh giới trang PDF ({len(page_boundaries)} trang)")
            page_texts = []  # [(page_num, start_offset, end_offset), ...]
            for idx_pb, (start_off, pg_num) in enumerate(page_boundaries):
                if idx_pb + 1 < len(page_boundaries):
                    end_off = page_boundaries[idx_pb + 1][0] - 2  # -2 for '\n\n' separator
                else:
                    end_off = len(text)
                page_texts.append((pg_num, start_off, end_off))

            # Merge consecutive pages into groups of ~2000 chars
            group_start_idx = 0
            while group_start_idx < len(page_texts):
                group_chars = 0
                group_end_idx = group_start_idx
                while group_end_idx < len(page_texts):
                    pg_len = page_texts[group_end_idx][2] - page_texts[group_end_idx][1]
                    if group_chars > 0 and group_chars + pg_len > 2500:
                        break  # Don't exceed ~2500 chars per group
                    group_chars += pg_len
                    group_end_idx += 1

                if group_end_idx == group_start_idx:
                    group_end_idx = group_start_idx + 1  # At least 1 page per group

                first_pg = page_texts[group_start_idx][0]
                last_pg = page_texts[group_end_idx - 1][0]
                chunk_start = page_texts[group_start_idx][1]
                chunk_end = page_texts[group_end_idx - 1][2]
                chunk = text[chunk_start:chunk_end].strip()

                if len(chunk) > 200:
                    if first_pg != last_pg:
                        page_label = f"Trang {first_pg}-{last_pg}"
                    else:
                        page_label = f"Trang {first_pg}"

                    first_line = chunk.split('\n')[0].strip()
                    first_line = re.sub(r'  +', ' ', first_line)
                    first_line_truncated = _truncate_title_safely(first_line, max_length=300)

                    sections.append({
                        'chapter': 'Tài liệu',
                        'title': f'{page_label}: {first_line_truncated}',
                        'content': chunk,
                        'word_count': len(chunk.split()),
                        'char_count': len(chunk),
                        'page_num': first_pg,
                    })

                group_start_idx = group_end_idx
        else:
            # === LEGACY: No page boundaries → fixed-size chunks ===
            chunk_size = 2000
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i+chunk_size].strip()
                if len(chunk) > 300:
                    page_label = f"Đoạn {len(sections)+1}"

                    first_line = chunk.split('\n')[0].strip()
                    first_line = re.sub(r'  +', ' ', first_line)
                    first_line_truncated = _truncate_title_safely(first_line, max_length=300)

                    sections.append({
                        'chapter': 'Tài liệu',
                        'title': f'{page_label}: {first_line_truncated}',
                        'content': chunk,
                        'word_count': len(chunk.split()),
                        'char_count': len(chunk),
                    })
    
    # DEBUG: In ra thống kê sections theo chapter
    print(f"\n📖 ĐÃ TRÍCH XUẤT {len(sections)} SECTIONS:")
    chapter_stats = {}
    for idx, sec in enumerate(sections, 1):
        ch = sec.get('chapter') or 'Unknown'  # Đảm bảo không None
        if ch not in chapter_stats:
            chapter_stats[ch] = []
        chapter_stats[ch].append(sec['title'][:60])
    
    # In thống kê
    print(f"\n📊 Phân bố sections theo chapter:")
    sorted_chapters = sorted(chapter_stats.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    for ch in sorted_chapters:
        print(f"   {ch}: {len(chapter_stats[ch])} sections")
        # In chi tiết 2 sections đầu để debug
        for i, title in enumerate(chapter_stats[ch][:2]):
            print(f"      {i+1}. {title}...")
    
    # ⚠️ CẢNH BÁO nếu chỉ có 2 chương hoặc ít hơn
    unique_chapters = len([ch for ch in chapter_stats.keys() if ch != 'Unknown'])
    print(f"\n📊 TỔNG KẾT PARSE:")
    print(f"   ✅ Phát hiện: {unique_chapters} chương")
    print(f"   ✅ Tổng sections: {len(sections)}")
    
    if unique_chapters <= 2:
        print(f"\n⚠️⚠️  CHỈ PHÁT HIỆN {unique_chapters} CHƯƠNG!")
        print(f"   → PDF có thể bị cắt ngắn hoặc format không đồng nhất")
        print(f"   → Kiểm tra:")
        print(f"      1. PDF gốc có đầy đủ tất cả chương không?")
        print(f"      2. Số chương trong PDF thực tế là bao nhiêu?")
        print(f"      3. Format tiêu đề chương: 'Chương X' hay 'X.1 Tiêu đề'?")
    else:
        print(f"   🎉 Tốt! PDF có {unique_chapters} chương - sẽ sinh câu hỏi đều tất cả")
    
    # ⚠️ CẢNH BÁO nếu chỉ có 2 chương
    unique_chapters = len([ch for ch in chapter_stats.keys() if ch != 'Unknown'])
    if unique_chapters <= 2:
        print(f"\n⚠️️  CHỈ PHÁT HIỆN {unique_chapters} CHƯƠNG!")
        print(f"   → PDF có thể bị cắt ngắn hoặc format không đồng nhất")
        print(f"   → Kiểm tra PDF gốc xem có đầy đủ tất cả chương không")
        # In chi tiết từng section
        print(f"   [{idx}] Ch={ch} | Title='{sec['title'][:70]}' | Content='{sec['content'][:80]}...'")
    
    print(f"\n📊 Thống kê theo Chương:")
    for ch in sorted(chapter_stats.keys()):
        print(f"   {ch}: {len(chapter_stats[ch])} mục")
    
    return sections
    
    # In stats - sắp xếp an toàn
    try:
        sorted_chapters = sorted(chapter_stats.keys())
    except TypeError:
        # Fallback nếu có None hoặc lỗi compare
        sorted_chapters = [k for k in chapter_stats.keys() if k] + [k for k in chapter_stats.keys() if not k]
    
    for ch in sorted_chapters:
        print(f"  ├─ {ch}: {len(chapter_stats[ch])} sections")
        for title in chapter_stats[ch][:2]:
            print(f"  │    • {title}...")
        if len(chapter_stats[ch]) > 2:
            print(f"  │    ... và {len(chapter_stats[ch])-2} sections nữa")
    
    for ch, titles in chapter_stats.items():
        print(f"  ├─ {ch}: {len(titles)} sections")
        for t in titles[:3]:  # Chỉ in 3 sections đầu
            print(f"  │    • {t}...")
        if len(titles) > 3:
            print(f"  │    ... và {len(titles)-3} sections khác")
    print()
    
    return sections
