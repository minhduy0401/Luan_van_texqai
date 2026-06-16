# utils/helpers.py – Answer formatting, points calculation, PDF font helpers
import re
import os

# --- LOGIC GIẢI THUẬT (Dành cho so sánh trong luận văn) ---

def clean_answer_formatting(answer):
    """Làm sạch dấu ** (markdown bold) và [] khỏi câu trả lời để hiển thị đẹp hơn"""
    if not answer:
        return answer
    
    # Bỏ tất cả dấu ** (markdown bold)
    cleaned = answer.replace('**', '')
    
    # Bỏ dấu __ (markdown italic)
    cleaned = cleaned.replace('__', '')
    
    # Bỏ dấu * đơn (italic)
    cleaned = re.sub(r'(?<!\*)\*(?!\*)', '', cleaned)
    
    # Bỏ dấu [] nếu bọc tiêu đề (ví dụ: [Tiêu đề] → Tiêu đề)
    # Nhưng giữ lại dấu [] trong nội dung (ví dụ: [1], [2])
    cleaned = re.sub(r'^\[(.*?)\]$', r'\1', cleaned, flags=re.MULTILINE)
    
    # Bỏ "Nội dung:" ở đầu dòng (AI đôi khi copy từ prompt format)
    cleaned = re.sub(r'^\s*Nội dung:\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*NỘI DUNG:\s*', '', cleaned, flags=re.MULTILINE)
    
    # Bỏ các cụm từ dẫn nhập thừa ("theo tài liệu", "dựa trên tài liệu", ...)
    filler_patterns = [
        r'[Tt]heo tài liệu,?\s*',
        r'[Dd]ựa trên tài liệu,?\s*',
        r'[Tt]rong giáo trình,?\s*',
        r'[Tt]ài liệu cho thấy,?\s*',
        r'[Tt]ài liệu nêu rõ,?\s*',
        r'[Tt]ài liệu chỉ ra rằng,?\s*',
        r'[Tt]ài liệu chỉ ra,?\s*',
        r'[Nn]hư đã nêu trong tài liệu,?\s*',
        r'[Nn]hư đã đề cập,?\s*',
        r'[Nn]hư đã trình bày,?\s*',
        r'[Dd]ựa vào nội dung tài liệu,?\s*',
        r'[Tt]heo như tài liệu,?\s*',
        r'[Dd]ựa trên nội dung giáo trình,?\s*',
        r'[Dd]ựa theo tài liệu,?\s*',
        r'[Dd]ược đề cập trong tài liệu,?\s*',
        r'[Tt]heo giáo trình,?\s*',
    ]
    for pat in filler_patterns:
        cleaned = re.sub(pat, '', cleaned)

    # Bỏ các câu thừa/lan man không chứa thông tin mới
    filler_sentence_patterns = [
        r'[Vv]iệc này (?:rất |vô cùng )?quan trọng[^.]*\.\s*',
        r'[Đđ]iều này cho thấy[^.]*\.\s*',
        r'[Cc]ó thể thấy rằng,?\s*',
        r'[Nn]hư vậy,?\s*',
        r'[Tt]óm lại,?\s*',
        r'[Tt]ừ đó cho thấy,?\s*',
        r'[Qq]ua đó,?\s*',
        r'[Nn]hìn chung,?\s*',
        r'[Tt]ừ những (?:phân tích|điều) trên,?\s*',
        r'[Cc]hính vì vậy,?\s*',
        r'[Đđ]ây là (?:một )?(?:vấn đề|điều|yếu tố) (?:rất |vô cùng )?quan trọng[^.]*\.\s*',
        r'[Đđ]iều này (?:rất |vô cùng )?(?:quan trọng|cần thiết)[^.]*\.\s*',
        r'[Nn]ói cách khác,?\s*',
        r'[Cc]ần lưu ý rằng,?\s*',
        r'[Tt]heo đó,?\s*',
    ]
    for pat in filler_sentence_patterns:
        cleaned = re.sub(pat, '', cleaned)
    
    return cleaned

def calculate_points_from_bloom(bloom_level, custom_points=None):
    """Tính điểm dựa trên cấp độ Bloom và tạo breakdown 0.25đ/ý"""
    # Điểm mặc định cho từng cấp Bloom (có thể tùy chỉnh)
    default_points = {
        'Bloom 1': 1.0,    # 4 ý
        'Bloom 2': 1.5,    # 6 ý
        'Bloom 3': 2.0,    # 8 ý
        'Bloom 4': 2.5,    # 10 ý
        'Bloom 5': 3.0,    # 12 ý
        'Bloom 6': 3.5     # 14 ý
    }
    
    # Lấy cấp độ Bloom (Bloom 1, Bloom 2, ...)
    bloom_key = bloom_level.split('(')[0].strip() if '(' in bloom_level else bloom_level.strip()
    
    # Sử dụng điểm tùy chỉnh hoặc mặc định
    total = custom_points if custom_points else default_points.get(bloom_key, 1.0)
    
    # Tính số ý (mỗi ý 0.25 điểm)
    sub_count = int(total / 0.25)
    
    # Tạo breakdown chi tiết
    breakdown = []
    for i in range(1, sub_count + 1):
        breakdown.append(f"Ý {i}: 0.25đ")
    
    breakdown_text = " | ".join(breakdown)
    
    return total, sub_count, breakdown_text

def _get_pdf_font_name_for_windows():
    """Đăng ký font Unicode để PDF hiển thị tiếng Việt tốt hơn."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        if 'ArialUnicodeVN' in pdfmetrics.getRegisteredFontNames():
            return 'ArialUnicodeVN'

        candidate_paths = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\times.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]

        for font_path in candidate_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('ArialUnicodeVN', font_path))
                return 'ArialUnicodeVN'
    except Exception as e:
        print(f"⚠️ Không đăng ký được font Unicode cho PDF: {e}")

    return 'Helvetica'

def _draw_wrapped_pdf_text(pdf_canvas, text, x, y, max_width, font_name='Helvetica', font_size=11, line_height=16):
    """Vẽ text nhiều dòng trong PDF và trả về toạ độ y sau khi vẽ."""
    try:
        from reportlab.pdfbase import pdfmetrics
    except Exception:
        return y

    if not text:
        return y

    words = str(text).replace('\n', ' \n ').split()
    current_line = []

    for word in words:
        if word == '\\n':
            if current_line:
                pdf_canvas.drawString(x, y, ' '.join(current_line))
                y -= line_height
                current_line = []
            y -= 4
            continue

        candidate = ' '.join(current_line + [word])
        line_width = pdfmetrics.stringWidth(candidate, font_name, font_size)

        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                pdf_canvas.drawString(x, y, ' '.join(current_line))
                y -= line_height
            current_line = [word]

    if current_line:
        pdf_canvas.drawString(x, y, ' '.join(current_line))
        y -= line_height

    return y


def localize_section_info(text: str, lang: str = 'vi') -> str:
    """Đổi nhãn Chương/Mục/Trang sang Chapter/Section/Page khi lang='en'."""
    if not text or lang != 'en':
        return text or ''

    result = text
    for pattern, repl in (
        (r'\bChương\s+', 'Chapter '),
        (r'\bCHUONG\s+', 'Chapter '),
        (r'\bMục\s+', 'Section '),
        (r'\bMUC\s+', 'Section '),
        (r'\bPhần\s+', 'Part '),
        (r'\bPHẦN\s+', 'Part '),
        (r'\bBài\s+', 'Lesson '),
        (r'\bTrang\s+', 'Page '),
        (r'\bNội dung\b', 'Content'),
    ):
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)

    # "Chapter 1 - Section Chapter 1: ..." → "Chapter 1: ..."
    result = re.sub(
        r'^(Chapter\s+\d+)\s*-\s*Section\s+\1\s*:\s*',
        r'\1: ',
        result,
        flags=re.IGNORECASE,
    )
    return result


def format_section_info(chapter, sec_num, display_title, page_num=None, lang='vi'):
    """Xây dựng chuỗi section_info hiển thị trên UI."""
    chapter_display = localize_section_info(chapter, lang) if lang == 'en' else chapter
    if lang == 'en' and chapter_display == chapter and chapter == 'Nội dung':
        chapter_display = 'Content'

    if sec_num:
        sec_display = localize_section_info(sec_num, lang) if lang == 'en' else sec_num
        if lang == 'en':
            chap_m = re.match(r'^Chapter\s+(\d+)', chapter_display, re.IGNORECASE)
            sec_m = re.match(r'^Chapter\s+(\d+)', sec_display, re.IGNORECASE)
            if chap_m and sec_m and chap_m.group(1) == sec_m.group(1):
                return f"{chapter_display}: {display_title}"
        sec_label = 'Section' if lang == 'en' else 'Mục'
        return f"{chapter_display} - {sec_label} {sec_display}: {display_title}"

    if page_num:
        page_label = 'Page' if lang == 'en' else 'Trang'
        return f"{page_label} {page_num}: {display_title}"

    return f"{chapter_display}: {display_title}"


def _bloom_ui_label(bloom_level: str, lang: str) -> str:
    if lang == 'en':
        from utils.translations import TRANSLATIONS
        return TRANSLATIONS.get(bloom_level, {}).get('en', bloom_level)
    return bloom_level


def progress_analyzing_document(lang='vi'):
    return 'Analyzing document...' if lang == 'en' else 'Đang phân tích tài liệu...'


def progress_generating_question(current, total, bloom_level, lang='vi'):
    bloom = _bloom_ui_label(bloom_level, lang)
    if lang == 'en':
        return f'Generating question {current}/{total} ({bloom})...'
    return f'Đang sinh câu {current}/{total} ({bloom})...'


def progress_pipeline_complete(generated, total, lang='vi'):
    if lang == 'en':
        return f'Completed! Generated {generated}/{total} questions.'
    return f'Hoàn tất! Đã sinh {generated}/{total} câu hỏi.'


def progress_saving_results(lang='vi'):
    return 'Saving results to database...' if lang == 'en' else 'Đang lưu kết quả vào cơ sở dữ liệu...'


def progress_init_pipeline(lang='vi'):
    return 'Initializing AI pipeline...' if lang == 'en' else 'Đang khởi động pipeline...'


def progress_reading_textbook(lang='vi'):
    return 'Reading textbook...' if lang == 'en' else 'Đang đọc giáo trình...'


def progress_reading_page(page_num, total_pages, label='', lang='vi'):
    if lang == 'en':
        base = f'Reading textbook... page {page_num}/{total_pages}'
    else:
        base = f'Đang đọc giáo trình... trang {page_num}/{total_pages}'
    return f'{base} ({label})' if label else base


def progress_textbook_saved(lang='vi'):
    return 'Textbook read. Saving document...' if lang == 'en' else 'Đã đọc xong giáo trình. Đang lưu tài liệu...'


def progress_job_complete(generated, total, lang='vi'):
    if lang == 'en':
        return f'Completed! Generated {generated}/{total} questions.'
    return f'Hoàn thành! Đã tạo {generated}/{total} câu hỏi.'


def progress_flash_success(generated, total, lang='vi'):
    if lang == 'en':
        return f'Successfully generated {generated}/{total} questions!'
    return f'Đã tạo thành công {generated}/{total} câu hỏi!'


def progress_error(exc, lang='vi'):
    return f'Error: {exc}' if lang == 'en' else f'Lỗi: {exc}'
