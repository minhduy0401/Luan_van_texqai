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
