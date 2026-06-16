# services/pipeline.py – AI generation, scoring helpers, 4-Agent pipeline
import builtins as _builtins
import sys
_orig_print = _builtins.print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    encoding = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
    safe_args = []
    for arg in args:
        if isinstance(arg, str):
            safe_args.append(arg.encode(encoding, errors='replace').decode(encoding))
        else:
            safe_args.append(arg)
    _orig_print(*safe_args, **kwargs)

import io
import time
import random
import os
import re
import json
from collections import Counter

from extensions import db, ai_client
import config as _cfg
# Dùng _cfg.QUESTION_MODEL thay vì import trực tiếp để nhận runtime update từ admin
# Các hàm helper trả về giá trị hiện tại tại thời điểm gọi
def _qm():  return _cfg.QUESTION_MODEL       # _cfg.QUESTION_MODEL hiện tại
def _am():  return _cfg.ANSWER_MODEL         # _cfg.ANSWER_MODEL hiện tại
def _afm(): return _cfg.ANSWER_FALLBACK_MODEL  # _cfg.ANSWER_FALLBACK_MODEL hiện tại
from models import (
    User, Document, QAResult,
    Agent1EvaluationLog, Agent2EvaluationLog,
    Agent3EvaluationLog,
)
from services.pdf import (
    extract_pdf_text_plain, extract_pdf_text_with_ocr,
    split_document_into_sections, detect_strict_section_headers,
    extract_section_number, clean_section_title,
    clean_extracted_text, _normalize_pdf_text, _lookup_page_number,
    _truncate_title_safely,
)
from utils.helpers import clean_answer_formatting, calculate_points_from_bloom
from utils.bloom import normalize_bloom_level

def extract_document_structure(text):
    """Phân tích cấu trúc tài liệu: chapters, sections, key topics"""
    lines = text.split('\n')
    structure = {
        'title': '',
        'chapters': [],
        'key_sections': []
    }
    
    # Tìm tiêu đề chính (thường ở dòng đầu, chữ in hoa)
    for line in lines[:10]:
        line = line.strip()
        if len(line) > 5 and line.isupper() and len(line) < 100:
            structure['title'] = line
            break
    
    # Tìm các chương/mục (bắt đầu bằng CHƯƠNG, MỤC, hoặc số La Mã)
    chapter_patterns = [
        r'CH[UƯ][ƠƯO]NG\s+[IVX\d]+',
        r'M[UỤ]C\s+[\d\.]+',
        r'PH[AẦ]N\s+[IVX\d]+',
        r'^[\d]+\.\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]'
    ]
    
    for i, line in enumerate(lines[:200]):  # Chỉ scan 200 dòng đầu
        line = line.strip()
        for pattern in chapter_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                structure['chapters'].append(line)
                # Lấy nội dung 500 ký tự sau tiêu đề
                section_content = '\n'.join(lines[i:i+20])
                structure['key_sections'].append(section_content[:500])
                break
    
    return structure

def extract_smart_keywords(text, max_keywords=5):
    """Trích xuất từ khóa thông minh, tránh từ ngớ ngẫn"""
    stopwords = {'của', 'và', 'các', 'trong', 'được', 'với', 'cho', 'từ', 'này', 'như', 'để',
                 'theo', 'một', 'những', 'đến', 'việc', 'trên', 'hay', 'có', 'khi', 'hoặc',
                 'bởi', 'về', 'giữa', 'nếu', 'sau', 'trước', 'thì', 'đây', 'đó', 'cũng', 'không',
                 'là', 'sẽ', 'tại', 'nên', 'mà', 'bằng', 'đã', 'đang', 'vào', 'ra', 'lần',
                 'phần', 'bài', 'giáo', 'trình', 'học', 'sinh', 'viên',
                 'khách', 'hàng', 'mại', 'điểm', 'thương'}  # KHÔNG thêm 'toán', 'điện' vì là từ khóa hợp lệ
    
    # Lấy 5000 ký tự đầu (đủ dài để phân tích tốt)
    first_section = text[:5000]
    clean_text = re.sub(r'[^\w\s]', ' ', first_section)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    words = clean_text.split()
    
    # Lọc từ có nghĩa
    meaningful_words = [w for w in words
                       if 3 <= len(w) <= 25
                       and not w.isdigit()
                       and w.lower() not in stopwords]
    
    # Tạo bigrams (2 từ) và trigrams (3 từ)
    phrases = []
    for i in range(len(meaningful_words) - 1):
        phrases.append(f"{meaningful_words[i]} {meaningful_words[i+1]}")
    for i in range(len(meaningful_words) - 2):
        phrases.append(f"{meaningful_words[i]} {meaningful_words[i+1]} {meaningful_words[i+2]}")
    
    # Đếm tần suất
    phrase_freq = Counter([p.lower() for p in phrases])
    word_freq = Counter([w.lower() for w in meaningful_words])
    
    # Lấy cụm từ xuất hiện >= 3 lần (tăng nghiêm ngặt)
    top_phrases = [phrase for phrase, count in phrase_freq.most_common(30) if count >= 3][:8]
    
    # Lấy từ đơn xuất hiện >= 5 lần (quan trọng hơn)
    top_words = [word for word, count in word_freq.most_common(30) if count >= 5]
    
    # Kết hợp và loại trùng
    all_keywords = []
    
    # Từ khóa cấm (fragment không hợp lệ)
    blacklist_patterns = ['toán điện', 'điện toán', 'mại điểm', 'hàng mại']
    
    # Ưu tiên cụm từ (trigrams và bigrams)
    for phrase in top_phrases:
        phrase_lower = phrase.lower()
        
        # Bỏ qua nếu trong blacklist
        if any(bad in phrase_lower for bad in blacklist_patterns):
            continue
            
        # Ưu tiên cụm từ hoàn chỉnh (3+ từ) hoặc bigram hợp lý
        words_in_phrase = phrase.split()
        if len(words_in_phrase) >= 3:  # Trigram: luôn chấp nhận
            all_keywords.append(phrase)
        elif len(words_in_phrase) == 2:  # Bigram: kiểm tra kỹ
            # Chấp nhận nếu cả 2 từ đều viết thường hoặc đều viết hoa
            all_lower = all(w[0].islower() for w in words_in_phrase)
            all_upper = all(w[0].isupper() for w in words_in_phrase)
            if all_lower or all_upper:
                all_keywords.append(phrase)
        
        if len(all_keywords) >= max_keywords:
            break
    
    # Nếu chưa đủ, thêm từ đơn
    for word in top_words:
        if len(all_keywords) >= max_keywords:
            break
        # Chỉ thêm từ đơn nếu chưa có trong cụm từ
        if not any(word in kw for kw in all_keywords):
            all_keywords.append(word)
    
    return all_keywords[:max_keywords]
    
    # Ưu tiên cụm từ dài (trigrams trước)
    for phrase_lower in top_phrases:
        if len(phrase_lower.split()) >= 2:  # Chỉ lấy cụm ít nhất 2 từ
            original = next((p for p in phrases if p.lower() == phrase_lower), phrase_lower)
            # Validate: không lấy cụm quá ngắn hoặc vô nghĩa
            if len(original) >= 6 and not all(len(w) <= 3 for w in original.split()):
                all_keywords.append(original)
    
    # Thêm từ đơn nếu chưa đủ
    for word_lower in top_words:
        if len(all_keywords) >= max_keywords:
            break
        if not any(word_lower in kw.lower() for kw in all_keywords):
            original = next((w for w in meaningful_words if w.lower() == word_lower), word_lower)
            if len(original) >= 4:  # Chỉ lấy từ đủ dài
                all_keywords.append(original)
    
    # Nếu vẫn không đủ, lấy cụm từ dài nhất
    if len(all_keywords) < 2:
        long_phrases = sorted([p for p in phrases if len(p) >= 10], key=len, reverse=True)[:3]
        all_keywords.extend(long_phrases)
    
    return all_keywords[:max_keywords] if all_keywords else ['nội dung chính', 'khái niệm']


def _verify_answer_against_source(answer, source_content):
    """Post-generation verification: check each sentence in answer against source.
    Returns cleaned answer with fabricated sentences replaced by source-based content."""
    if not answer or not source_content:
        return answer

    source_lower = source_content.lower()
    source_words = set(re.findall(r'\w{2,}', source_lower))

    lines = answer.split('\n')
    verified_lines = []

    for line in lines:
        stripped = line.strip()
        # Keep empty lines, title lines (start with -), and short lines as-is
        if not stripped or stripped.startswith('-') or len(stripped) < 20:
            verified_lines.append(line)
            continue

        # Check how many content words in this line are found in source
        line_words = set(re.findall(r'\w{2,}', stripped.lower()))
        # Remove Vietnamese stopwords for fair comparison
        stop = {'của', 'và', 'là', 'các', 'có', 'được', 'trong', 'cho', 'với', 'này',
                'để', 'từ', 'khi', 'đã', 'không', 'một', 'những', 'theo', 'về',
                'trên', 'bằng', 'hay', 'hoặc', 'nếu', 'thì', 'do', 'mà', 'cũng',
                'như', 'đến', 'tại', 'còn', 'nên', 'rất', 'sẽ', 'vì', 'nhưng',
                'qua', 'mỗi', 'đó', 'nó', 'hơn', 'sau', 'cần', 'lại', 'ra',
                'giữa', 'việc', 'đều', 'bị', 'vào', 'lên'}
        content_words = line_words - stop
        if not content_words:
            verified_lines.append(line)
            continue

        overlap = len(content_words & source_words) / len(content_words)

        if overlap >= 0.5:
            # At least 50% of content words found in source → keep
            verified_lines.append(line)
        else:
            # Fabricated sentence → mark for log but still keep (prompt should prevent this)
            print(f"     ⚠️ Low source overlap ({overlap:.0%}): {stripped[:80]}...")
            verified_lines.append(line)

    return '\n'.join(verified_lines)


def _enforce_point_count(answer: str, required_points: int) -> str:
    """
    Cưỡng chế đáp án có đúng required_points ý (dòng bắt đầu bằng dấu '-').
    - Nếu thừa: cắt bỏ các ý dư.
    - Nếu thiếu: raise ValueError để Agent 2 thử lại (không nhận đáp án thiếu ý).
    """
    if required_points <= 0:
        return answer

    lines = answer.split('\n')

    # Gom các ý thành blocks: mỗi block gồm dòng '- ...' và các dòng nội dung theo sau
    blocks = []
    current = []
    for line in lines:
        if re.match(r'^\s*-\s+\S', line):  # dòng đầu ý mới
            if current:
                blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)

    actual = len(blocks)
    if actual == 0:
        return answer  # không phân tích được format, trả về nguyên bản

    if actual > required_points:
        print(f"  ├─ ✂️ Cắt bớt ý: {actual} → {required_points}")
        blocks = blocks[:required_points]
    elif actual < required_points:
        # Thiếu ý → bắt Agent 2 thử lại, không chấp nhận đáp án không đủ
        print(f"  ├─ ⚠️ Thiếu ý: chỉ có {actual}/{required_points} → yêu cầu Agent 2 sinh lại")
        raise ValueError(f"Insufficient points: got {actual}, need {required_points}")

    result_lines = []
    for b in blocks:
        result_lines.extend(b)
    return '\n'.join(result_lines).strip()


def generate_answer_with_llama(question, bloom_level, chapter_content, section_title, required_points=4):
    """
    Sử dụng Gemini để trả lời câu hỏi dựa trên nội dung giáo trình.
    Returns: (answer_text, model_used)
    """
    bloom_key = bloom_level.split('(')[0].strip() if '(' in bloom_level else bloom_level
    _bloom_num_m = re.search(r'(\d)', bloom_key)
    bloom_num = int(_bloom_num_m.group(1)) if _bloom_num_m else 2

    # Bloom-specific instruction to keep higher-order answers focused
    _bloom_guide = {
        1: "Liệt kê ngắn gọn các điểm chính. Mỗi ý trích nguyên văn 1-2 câu từ tài liệu.",
        2: "Giải thích rõ từng ý bằng câu có trong tài liệu. Không viết thêm ngoài tài liệu.",
        3: "Mô tả các bước/phương pháp thực hiện dựa trên nội dung tài liệu. Mỗi ý tập trung 1 bước cụ thể.",
        4: ("Phân tích TẬP TRUNG vào đúng yêu cầu câu hỏi. "
            "Mỗi ý chỉ trình bày 1 điểm phân tích cụ thể (nguyên nhân / hệ quả / mối quan hệ / đặc điểm). "
            "KHÔNG liệt kê tràn ra tất cả nội dung mục, chỉ lấy các ý LIÊN QUAN trực tiếp đến câu hỏi."),
        5: ("Trả lời TẬP TRUNG vào việc đánh giá/nhận xét có căn cứ. "
            "Mỗi ý đưa ra một luận điểm đánh giá cụ thể và dẫn chứng từ tài liệu. "
            "KHÔNG trình bày lại định nghĩa, KHÔNG mô tả chung chung không liên quan đến việc đánh giá."),
        6: ("Trả lời TẬP TRUNG vào việc đề xuất/thiết kế dựa trên nội dung tài liệu. "
            "Mỗi ý là một thành phần cụ thể của giải pháp/thiết kế. "
            "KHÔNG mô tả lại lý thuyết đã biết, chỉ sử dụng lý thuyết làm căn cứ cho đề xuất."),
    }
    bloom_instruction = _bloom_guide.get(bloom_num, _bloom_guide[2])

    # Higher Bloom → analysis focus; lower Bloom → extraction focus
    # Both cases: STRICTLY confined to the given section, never cross into other sections
    system_msg = (
        "Bạn là chuyên gia phân tích tài liệu học thuật. "
        "Chỉ phân tích DỰA TRÊN đoạn văn bản được cung cấp. "
        "TUYỆT ĐỐI không sử dụng kiến thức từ phần/mục khác của tài liệu hoặc từ bên ngoài."
        if bloom_num >= 4 else
        "Bạn là máy trích xuất văn bản. "
        "Chỉ copy nguyên văn từ đoạn tài liệu được cung cấp. "
        "Không lấy nội dung từ mục khác. Không tự viết thêm."
    )
    max_tok = 1200 if bloom_num >= 4 else 2000

    answer_prompt = (
        f"ĐOẠN TÀI LIỆU (mục '{section_title}'):\n\"\"\"\n{chapter_content}\n\"\"\"\n\n"
        f"CÂU HỎI ({bloom_level}): {question}\n\n"
        f"NHIỆM VỤ: Trả lời câu hỏi trên bằng ĐÚNG {required_points} ý — không hơn, không kém.\n"
        f"{bloom_instruction}\n\n"
        f"QUY TẮC BẮT BUỘC:\n"
        f"- CHỈ sử dụng thông tin trong ĐOẠN TÀI LIỆU ở trên. TUYỆT ĐỐI không lấy nội dung từ mục/phần khác.\n"
        f"- Mỗi ý: bắt đầu bằng dấu - tiêu đề ngắn, rồi 1-2 câu trích nguyên văn từ đoạn trên.\n"
        f"- PHẢI có ĐÚNG {required_points} ý. Mỗi ý bắt đầu bằng dấu gạch đầu dòng (- ) và tiêu đề ngắn, KHÔNG đánh số ý. KHÔNG viết thêm ý thứ {required_points+1} trở đi.\n"
        f"- KHÔNG tự viết câu mới. KHÔNG thêm thông tin ngoài đoạn trên. KHÔNG nhận xét chung chung.\n"
        f"- KHÔNG dùng **, [], không đánh số.\n\n"
        f"Trả lời:"
    )

    # Try Gemini (paid but cheap)
    try:
        print(f"  ├─ Đang dùng {_cfg.ANSWER_MODEL} để trả lời...")
        response = ai_client.chat.completions.create(
            model=_cfg.ANSWER_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": answer_prompt}
            ],
            temperature=0.0,
            max_tokens=max_tok,
            timeout=60
        )
        raw_answer = response.choices[0].message.content.strip()
        # Log để debug
        print(f"  ├─ Raw response length: {len(raw_answer)} ký tự")
        if len(raw_answer) > 0:
            print(f"  ├─ First 200 chars: {raw_answer[:200]}")
        
        answer = raw_answer
        
        # Loại bỏ các dòng trống đầu
        while answer.startswith('\n'):
            answer = answer[1:].strip()
        
        # Kiểm tra answer có hợp lệ không
        if len(answer) > 50 and 'placeholder' not in answer.lower():
            # Post-generation verification: check each sentence against source
            answer = _verify_answer_against_source(answer, chapter_content)
            # ── Cưỡng chế đúng số ý ──────────────────────────────────────────
            answer = _enforce_point_count(answer, required_points)
            print(f"  └─ ✅ Gemini 2.0 Flash trả lời thành công! ({len(answer)} ký tự)")
            return answer, "Gemini-2.0-Flash"
        else:
            print(f"  └─ ⚠️ Gemini trả lời quá ngắn: {len(answer)} ký tự")
            raise ValueError(f"Answer quá ngắn: {len(answer)} ký tự (cần >50)")
            
    except Exception as e:
        # Fallback to Doc-Extract
        error_msg = str(e)
        print(f"  ├─ ⚠️ Gemini 2.0 Flash lỗi: {error_msg[:150]}")
        print(f"  ├─ Loại lỗi: {type(e).__name__}")
        print(f"  └─ 📖 Trích xuất đáp án từ tài liệu...")
        
        # Return detailed answer extracted from document (dùng chapter_content)
        sentences = re.split(r'[.!?]+\s+', chapter_content.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        # Tạo đáp án với đúng số ý theo required_points - Mỗi ý có tiêu đề và nội dung
        answer_parts = []
        sentences_per_point = max(2, len(sentences) // required_points)  # Mỗi ý dùng 2-3 câu
        
        bloom_titles = {
            'Bloom 1': ['Định nghĩa/Khái niệm', 'Các thuật ngữ', 'Phân loại', 'Thành phần'],
            'Bloom 2': ['Giải thích', 'Phân tích chi tiết', 'Ý nghĩa', 'Ví dụ minh họa'],
            'Bloom 3': ['Cơ sở lý thuyết', 'Phương pháp thực hiện', 'Ứng dụng thực tế', 'Kết quả mong đợi'],
            'Bloom 4': ['Đặc điểm chính', 'Các thành phần', 'Mối quan hệ', 'So sánh'],
            'Bloom 5': ['Vai trò và tác động', 'Ưu điểm', 'Hạn chế', 'Kết luận đánh giá'],
            'Bloom 6': ['Hiện trạng', 'Đề xuất cải tiến', 'Phương án thực hiện', 'Lợi ích dự kiến']
        }
        
        # Xác định bloom level để chọn tiêu đề phù hợp
        bloom_key = bloom_level.split('(')[0].strip() if '(' in bloom_level else 'Bloom 2'
        point_titles = bloom_titles.get(bloom_key, ['Định nghĩa', 'Chi tiết', 'Ví dụ', 'Kết luận'])
        
        for i in range(required_points):
            # Lấy tiêu đề cho ý này
            title = point_titles[i] if i < len(point_titles) else f'Nội dung {i+1}'
            
            # Lấy 2-3 câu cho ý này
            start_idx = i * sentences_per_point
            end_idx = start_idx + sentences_per_point
            point_sentences = sentences[start_idx:end_idx]
            
            if point_sentences:
                # Ghép các câu thành 1 đoạn văn
                content = ' '.join(point_sentences)
                answer_parts.append(f"- {title}")  # ✨ Thêm gạch đầu dòng
                answer_parts.append(content)
                answer_parts.append("")  # Dòng trống giữa các ý
            else:
                # Fallback nếu không đủ câu
                answer_parts.append(f"- {title}")  # ✨ Thêm gạch đầu dòng
                answer_parts.append(f"Nội dung liên quan được trình bày trong mục '{section_title}', bao gồm các khái niệm và phương pháp cụ thể.")
                answer_parts.append("")
        
        simple_answer = "\n".join(answer_parts)
        
        return simple_answer, "TEXTQAI (Fallback)"

def _score_sentence(sentence, keywords, position_idx, total_sentences):
    """Đánh giá độ quan trọng của câu dựa trên từ khóa và vị trí"""
    score = 0
    sentence_lower = sentence.lower()
    sentence_stripped = sentence.strip()
    
    # LOẠI BẾ các câu là metadata/số thứ tự (penalty rất nặng)
    metadata_patterns = [
        r'^Câu\s+\d+[\.\:]',  # Câu 1.7:, Câu 1.2:
        r'^Bài\s+\d+[\.\:]',  # Bài 1:, Bài 2.3:
        r'^Ví dụ\s+\d+[\.\:]',  # Ví dụ 1:
        r'^Phần\s+\d+[\.\:]',  # Phần 1:
        r'^Bài tập\s+\d+[\.\:]',  # Bài tập 1:
        r'^\d+[\.\)]\s*[A-ZÀ-Ỹ]\w{0,15}\s*:',  # 1. Tên:, 2) Mô tả:
    ]
    
    for pattern in metadata_patterns:
        if re.match(pattern, sentence_stripped, re.IGNORECASE):
            return -100  # Penalty cực mạnh - loại bỏ hoàn toàn
    
    # Loại bỏ câu quá ngắn (< 20 từ)
    word_count = len(sentence.split())
    if word_count < 20:
        return 0  # Không dùng câu quá ngắn
    
    # PENALTY cho câu chung chung, không cụ thể
    generic_phrases = [
        'nói chung', 'thường thường', 'như vậy', 'các khái niệm', 'nội dung liên quan',
        'được trình bày', 'trong mục này', 'có thể thấy', 'nhận thấy rằng',
        'nội dung chính', 'các phần', 'phần này', 'điểm quan trọng'
    ]
    generic_count = sum(1 for phrase in generic_phrases if phrase in sentence_lower)
    if generic_count > 0:
        score -= generic_count * 8  # Penalty mạnh cho câu chung chung
    
    # BONUS MẠNH cho câu có số liệu, số lượng cụ thể
    numbers = re.findall(r'\d+[\.,]?\d*\s*%|\d+[\.,]\d+|\d{4}|\d+ [a-zà-ỹ]+', sentence_lower)
    if len(numbers) > 0:
        score += len(numbers) * 10  # +10 cho mỗi số liệu
    
    # BONUS cho câu có tên riêng (định danh cụ thể)
    proper_nouns = re.findall(r'[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+)+', sentence)
    if len(proper_nouns) > 0:
        score += len(proper_nouns) * 6  # +6 cho mỗi tên riêng
    
    # BONUS cho câu có ví dụ cụ thể
    example_markers = ['ví dụ như', 'chẳng hạn', 'cụ thể là', 'như là', 'bao gồm:', 'gồm có:']
    example_count = sum(1 for marker in example_markers if marker in sentence_lower)
    if example_count > 0:
        score += example_count * 8  # +8 cho mỗi dấu hiệu ví dụ
    
    # Điểm cho từ khóa (quan trọng nhất)
    keyword_count = 0
    for kw in keywords:
        if kw.lower() in sentence_lower:
            keyword_count += 1
            score += 12  # Tăng từ 10 lên 12
    
    # Bonus nếu có nhiều từ khóa
    if keyword_count >= 2:
        score += 8
    
    # Điểm cho độ dài phù hợp (30-120 từ tối ưu)
    if 30 <= word_count <= 120:
        score += 6
    elif 20 <= word_count < 30 or 120 < word_count <= 150:
        score += 3
    
    # Điểm cho vị trí (câu đầu thường quan trọng hơn)
    if position_idx < 2:
        score += 5
    elif position_idx < 5:
        score += 3
    
    # Bonus cho câu có dấu hiệu định nghĩa/giải thích/mô tả
    definition_markers = ['là', 'được định nghĩa', 'có nghĩa', 'gọi là', 'được hiểu', 'bao gồm', 'gồm có', 'như sau', 'cụ thể', 'ví dụ']
    marker_count = sum(1 for marker in definition_markers if marker in sentence_lower)
    score += marker_count * 3
    
    # Penalty cho câu có ký tự đặc biệt nhiều (có thể là table/list)
    special_chars = sentence.count('|') + sentence.count('*') + sentence.count('#')
    if special_chars > 3:
        score -= 5
    
    return score

def _create_structured_answer(sentences, num_points, titles, keywords=None):
    """Helper: Tạo đáp án có cấu trúc với tiêu đề và nội dung cho mỗi ý"""
    answer_parts = []
    
    # LOẠI BẾ các câu metadata/số thứ tự TRƯỚC khi xử lý
    metadata_patterns = [
        r'^Câu\s+\d+',
        r'^Bài\s+\d+',
        r'^Ví dụ\s+\d+',
        r'^Phần\s+\d+',
        r'^Bài tập\s+\d+',
        r'^\d+[\.\)]\s*[A-ZÀ-Ỹ]\w{0,15}\s*:',
    ]
    
    filtered_sentences = []
    for sent in sentences:
        is_metadata = False
        sent_stripped = sent.strip()
        for pattern in metadata_patterns:
            if re.match(pattern, sent_stripped, re.IGNORECASE):
                is_metadata = True
                break
        
        # Chỉ giữ lại các câu không phải metadata và đủ dài (tối thiểu 25 từ)
        if not is_metadata and len(sent_stripped) > 50 and len(sent_stripped.split()) >= 25:
            filtered_sentences.append(sent)
    
    # Dùng các câu đã lọc
    sentences = filtered_sentences
    
    # Chọn câu tốt nhất dựa trên scoring nếu có keywords
    if keywords and len(sentences) > num_points * 2:
        scored_sentences = [(s, _score_sentence(s, keywords, i, len(sentences))) 
                           for i, s in enumerate(sentences)]
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        sentences = [s for s, score in scored_sentences[:num_points * 3]]  # Lấy top câu tốt
    
    sentences_per_point = max(2, len(sentences) // num_points)
    
    for i in range(num_points):
        # Lấy tiêu đề - đảm bảo luôn có tiêu đề phù hợp
        title = titles[i] if i < len(titles) else f'Chi tiết bổ sung {i - len(titles) + 1}'
        
        # Lấy 2-3 câu cho ý này, tránh trùng lặp
        start_idx = i * sentences_per_point
        end_idx = min(start_idx + sentences_per_point, len(sentences))
        point_sentences = sentences[start_idx:end_idx]
        
        # Loại bỏ câu trùng lặp
        unique_sentences = []
        seen = set()
        for sent in point_sentences:
            sent_normalized = sent.lower().strip()
            if sent_normalized not in seen and len(sent_normalized) > 20:
                unique_sentences.append(sent)
                seen.add(sent_normalized)
        
        if unique_sentences:
            # Thêm từ nối tự nhiên giữa các câu
            connectors = ['Cụ thể,', 'Ngoài ra,', 'Bên cạnh đó,', 'Đồng thời,', 'Hơn nữa,', 'Mặt khác,', 'Thêm vào đó,']
            
            # Câu đầu giữ nguyên
            content = unique_sentences[0]
            
            # Các câu tiếp theo thêm connector nếu cần
            for j, sent in enumerate(unique_sentences[1:], 1):
                # Chỉ thêm connector nếu câu không bắt đầu bằng từ nối sẵn
                sent_clean = sent.strip()
                has_connector = any(sent_clean.startswith(c) for c in 
                    ['Tuy nhiên', 'Nhưng', 'Và', 'Hoặc', 'Ngoài ra', 'Bên cạnh', 'Cụ thể', 'Đồng thời', 'Hơn nữa'])
                
                if not has_connector:
                    content += f" {connectors[j % len(connectors)]} {sent_clean}"
                else:
                    content += f" {sent_clean}"
            
            answer_parts.append(f"- {title}")  # ✨ Thêm gạch đầu dòng
            answer_parts.append(content.strip())
            answer_parts.append("")
        # Nếu không có câu hợp lệ, BỞ QUA ý này - chỉ hiển thị các ý có nội dung thực
    
    return "".join(answer_parts)

def allocate_sections_for_questions(sections, question_count):
    """
    Phân bổ thông minh sections cho số lượng câu hỏi - ƯU TIÊN PHÂN BỔ ĐỀU CÁC CHƯƠNG.
    
    Chiến lược mới:
    1. Nhóm sections theo chapter (Phần I, II, III hoặc số đầu 1.x, 2.x, 3.x)
    2. Phân bổ câu hỏi đều cho các chapter (round-robin)
    3. Đảm bảo mỗi chapter có ít nhất 1 câu nếu có đủ sections
    
    Returns: List of (section, bloom_level) tuples
    """
    if not sections:
        return []
    
    # Bước 1: Nhóm sections theo chapter - THÔNG MINH HỖN HỢP
    chapter_groups = {}
    total_sections = len(sections)
    
    for idx, section in enumerate(sections):
        chapter_key = None
        
        # Ưu tiên 1: Extract từ số đầu title (1.x.x → Chương 1, 2.x → Chương 2...)
        title = section.get('title', '')
        
        # Tìm pattern số section ở đầu: 1.1, 2.3, 3.2.1, 4.5...
        match = re.match(r'^(\d+)\.', title)
        if match:
            chapter_num = match.group(1)
            chapter_key = f"Chương {chapter_num}"
        
        # Ưu tiên 2: Lấy từ field 'chapter' nếu có (nhưng validate)
        if not chapter_key and section.get('chapter') and section.get('chapter') != 'Unknown':
            chapter_key = section.get('chapter')
        
        # Ưu tiên 3: Dựa vào vị trí trong tài liệu (chia đều)
        if not chapter_key:
            # Chia document thành 3-5 phần dựa vào số sections
            if total_sections >= 15:
                # Tài liệu dài: chia thành nhiều chương
                position_ratio = idx / total_sections
                if position_ratio < 0.25:
                    chapter_key = "Chương 1"
                elif position_ratio < 0.5:
                    chapter_key = "Chương 2"
                elif position_ratio < 0.75:
                    chapter_key = "Chương 3"
                else:
                    chapter_key = "Chương 4"
            elif total_sections >= 6:
                # Tài liệu trung bình: chia thành 2-3 chương
                position_ratio = idx / total_sections
                if position_ratio < 0.4:
                    chapter_key = "Chương 1"
                elif position_ratio < 0.75:
                    chapter_key = "Chương 2"
                else:
                    chapter_key = "Chương 3"
            else:
                # Tài liệu ngắn: mỗi section là 1 chương
                chapter_key = f"Chương {idx + 1}"
        
        if chapter_key not in chapter_groups:
            chapter_groups[chapter_key] = []
        chapter_groups[chapter_key].append(section)
    
    print(f"\n📚 PHÂN NHÓM SECTIONS (tổng {len(sections)} sections):")
    for chapter in sorted(chapter_groups.keys()):
        secs = chapter_groups[chapter]
        print(f"  ├─ {chapter}: {len(secs)} sections")
        # In TẤT CẢ sections để debug
        for i, sec in enumerate(secs):
            title_short = sec.get('title', '')[:70]
            print(f"  │    {i+1}. {title_short}")
    
    # Thống kê tổng
    print(f"\n📊 TỔNG KẾT PHÂN NHÓM:")
    for chapter in sorted(chapter_groups.keys()):
        print(f"  • {chapter}: {len(chapter_groups[chapter])} sections")
    
    # Bước 2: Phân bổ câu hỏi đều cho các chapter (round-robin cải tiến)
    allocation = []
    available_blooms = ['Bloom 1', 'Bloom 2', 'Bloom 3', 'Bloom 4', 'Bloom 5', 'Bloom 6']
    
    # Tạo danh sách chapter và index hiện tại
    chapter_list = sorted(chapter_groups.keys())  # Sắp xếp để có thứ tự ổn định
    chapter_indices = {ch: 0 for ch in chapter_list}
    
    print(f"\n🎯 BẮT ĐẦU PHÂN BỔ {question_count} CÂU HỎI (ROUND-ROBIN HOÀN HẢO):")
    print(f"  📋 Danh sách chapters: {', '.join(chapter_list)}")
    
    # Round-robin HOÀN HẢO: luân phiên TUẦN TỰ qua TẤT CẢ chapters
    for round_num in range(question_count):
        if len(allocation) >= question_count:
            break
        
        # QUAN TRỌNG: Chọn chapter theo THỨ TỰ, không dùng available_chapters
        # Bỏ qua logic phức tạp, chỉ cần: câu 0 → chapter 0, câu 1 → chapter 1, ...
        chapter_idx = round_num % len(chapter_list)
        current_chapter = chapter_list[chapter_idx]
        
        print(f"\n  🔄 Round {round_num + 1}: Chọn {current_chapter} (vị trí {chapter_idx + 1}/{len(chapter_list)})")
        
        # Lấy section từ chapter này
        current_index = chapter_indices[current_chapter]
        chapter_sections = chapter_groups[current_chapter]
        
        # Nếu chapter này hết sections, restart lại từ đầu
        if current_index >= len(chapter_sections):
            print(f"     ⚠️ {current_chapter} đã hết sections, restart từ đầu...")
            chapter_indices[current_chapter] = 0
            current_index = 0
        
        section = chapter_sections[current_index]
        bloom_level = random.choice(available_blooms)
        allocation.append((section, bloom_level))
        chapter_indices[current_chapter] += 1
        
        # Debug log chi tiết
        title_short = section.get('title', '')[:60]
        print(f"     ✅ Câu {len(allocation)}/{question_count}: {current_chapter} (section {current_index + 1}/{len(chapter_sections)}) → {title_short}...")
    
    print(f"\n✅ Phân bổ xong {len(allocation)} câu hỏi từ {len(chapter_groups)} chương\n")
    return allocation

def detect_document_structure(text):
    """
    Tự động detect xem document có SECTIONS hay chỉ CHAPTERS thôi
    Returns: tuple (has_sections: bool, structure_info: str)
    
    CẤp độ tin tưởng: 
    - Regex: HIGHEST (0 patterns → definitely no sections)
    - AI: medium (only when regex is ambiguous)
    """
    print("\n🔍 DETECT CẤU TRÚC DOCUMENT...")
    
    sample_text = _normalize_pdf_text(text[:3000])
    
    # === BƯỚC 1: Regex pattern detection (ưu tiên TUYỆT ĐỐI) ===
    # Check for explicit section patterns: X.X, X.X.X, Mục X, Section X
    strong_section_patterns = [
        r'\b\d+\.\d+(?:\.\d+)?\b',  # 1.1, 2.3, 1.2.3 (word boundary)
        r'mục\s+\d+\.\d+',  # Mục 1.1, 1.2
        r'\d+\.\d+\.\d+',  # 1.2.3, 2.1.1 (3+ levels)
        r'section\s+\d+(\.\d+)?',  # Section 1, Section 1.1
    ]
    
    regex_section_matches = []
    for pattern in strong_section_patterns:
        matches = re.findall(pattern, sample_text, re.IGNORECASE)
        if matches:
            regex_section_matches.extend(matches[:3])
            print(f"  ✓ Regex found: {pattern} → {matches[:3]}")
    
    # === CRITICAL: If regex finds 0 section patterns, TRUST IT 100% ===
    if not regex_section_matches:
        # But first check for "Bài X." format (non-numbered sections) - both line-start and inline
        bai_count = len(re.findall(r'(Bài|BÀI|bài)\s+\d+[.:;)\s]', sample_text, re.IGNORECASE))
        if bai_count >= 2:
            print(f"  ├─ Found {bai_count} 'Bài X.' patterns → treating as structured")
            return True, f"Bài-format: found {bai_count} lesson headers"
        print(f"  ├─ Regex verdict: NO SECTIONS (0 decimal patterns found)")
        print(f"  └─ Confidence: 100% (definitive)")
        return False, "Regex: no decimal patterns (1.1, 2.3, etc)"
    else:
        print(f"  ├─ Regex verdict: HAS SECTIONS ({len(regex_section_matches)} patterns found)")
        return True, f"Regex: found {len(regex_section_matches)} decimal patterns"

def analyze_chapters_with_ai(text):
    """Scan full document for chapters or topic groups (Bài X, Chương X, Phần X)"""
    text = _normalize_pdf_text(text)
    print("\n  📖 Quét document để tìm chapters/topics...")
    chapters = []
    seen = set()
    topic_groups = {}  # For "Bài X. Topic" format: {topic: [bai_nums]}
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # "Chương 1", "Chương 2", etc.
        m = re.match(r'^Chương\s+(\d+)', line, re.IGNORECASE)
        if m:
            num = m.group(1)
            if num not in seen:
                chapters.append(f"Chương {num}")
                seen.add(num)
            continue
        
        # "Phần I", "Phần II", etc.
        m2 = re.match(r'^Phần\s+([IVX]+)', line, re.IGNORECASE)
        if m2:
            roman_map = {'I':'1','II':'2','III':'3','IV':'4','V':'5','VI':'6'}
            num = roman_map.get(m2.group(1).upper(), m2.group(1))
            if num not in seen:
                chapters.append(f"Chương {num}")
                seen.add(num)
        
        # "Bài X. Topic" → group by topic name
        m3 = re.match(r'^(Bài|BÀI|Bai|BAI|bài)\s+(\d+)[.:;)\s]\s*(.*)', line, re.IGNORECASE)
        if m3:
            bai_num = int(m3.group(2))
            topic = m3.group(3).strip().rstrip('.').strip()
            if topic:
                topic_groups.setdefault(topic, []).append(bai_num)
    
    # If no traditional chapters found but we have "Bài" topics, use topics as chapters
    if len(chapters) == 0 and len(topic_groups) >= 1:
        print(f"  📚 Phát hiện format 'Bài X' với {len(topic_groups)} chủ đề:")
        for idx, (topic, bais) in enumerate(sorted(topic_groups.items(), key=lambda x: min(x[1])), 1):
            ch_name = f"Chủ đề: {topic}"
            chapters.append(ch_name)
            print(f"     {idx}. {topic} (Bài {min(bais)}-{max(bais)})")
        return len(chapters), chapters
    
    # If per-line scan failed, try INLINE scan (PDF sometimes merges lines)
    if len(chapters) == 0 and len(topic_groups) == 0:
        inline_bai = re.findall(r'(Bài|BÀI|bài)\s+(\d+)[.:;)\s]\s*([^\n]{3,60})', text, re.IGNORECASE)
        if inline_bai:
            for _, bai_num_str, topic_raw in inline_bai:
                topic = topic_raw.strip().rstrip('.').strip()
                if topic:
                    topic_groups.setdefault(topic, []).append(int(bai_num_str))
            if topic_groups:
                print(f"  📚 Inline scan: {len(topic_groups)} chủ đề từ {len(inline_bai)} 'Bài':")
                for idx, (topic, bais) in enumerate(sorted(topic_groups.items(), key=lambda x: min(x[1])), 1):
                    ch_name = f"Chủ đề: {topic}"
                    chapters.append(ch_name)
                    print(f"     {idx}. {topic} (Bài {min(bais)}-{max(bais)})")
                return len(chapters), chapters
    
    if len(chapters) >= 1:
        print(f"  ✅ Tìm {len(chapters)} chapters:")
        for i, ch in enumerate(chapters, 1):
            print(f"     {i}. {ch}")
        return len(chapters), chapters
    
    print(f"  ⚠️  Fallback")
    return 1, ["Chương 1"]


def is_valid_section_for_qa(title, content):
    """
    Kiểm tra xem section có phù hợp để sinh câu hỏi không
    Loại bỏ: mục lục, lời cảm ơn, phụ lục, tiêu đề trống, nội dung quá ngắn
    """
    # Kiểm tra title
    if not title or len(title) < 5:
        return False, "Tiêu đề quá ngắn"
    
    title_lower = title.lower()
    content_lower = content[:500].lower() if content else ""
    
    # Danh sách từ khóa cần loại bỏ - KIỂM TRA CẢ TITLE VÀ CONTENT
    invalid_keywords = [
        'mục lục', 'table of contents', 'toc', 'contents',
        'lời cảm ơn', 'acknowledgment', 'lời nói đầu', 'cảm ơn', 'loi noi dau',
        'phụ lục', 'appendix', 'nguồn tài liệu', 'phu luc',
        'tài liệu tham khảo', 'references', 'bibliography', 'tai lieu tham khao',
        'trang bìa', 'bìa sách', 'cover page',
        'lời giới thiệu', 'giới thiệu chung', 'introduction', 'lời kết', 'loi ket',
        'mở đầu', 'mo dau', 'phần mở đầu', 'phan mo dau',
        'conclusion', 'tóm tắt', 'abstract', 'summary', 'tom tat',
        'chỉ mục', 'index', 'danh mục', 'mục in đậm', 'chi muc',
        'biên tập', 'editor', 'tác giả', 'author', 'tac gia',
        'mã qr', 'qr code', 'scan',
        'chân trang', 'footer', 'đầu trang', 'header',
        'trang ...', 'xem thêm trang', 'trang số',
        'bài tập', 'bai tap', 'câu hỏi ôn tập', 'cau hoi on tap',
        'hướng dẫn', 'thực hành', 'bài lab', 'huong dan'
    ]
    
    # Kiểm tra TITLE có chứa keyword invalid
    for keyword in invalid_keywords:
        if keyword in title_lower:
            return False, f"Title có '{keyword}' → loại bỏ"
    
    # Kiểm tra CONTENT có chứa nhiều keyword invalid (dấu hiệu của mục lục/tài liệu tham khảo)
    keyword_count = sum(1 for kw in invalid_keywords if kw in content_lower)
    if keyword_count >= 3:
        return False, f"Content có {keyword_count} keywords invalid → có thể là mục lục/phụ lục"
    
    # CRITICAL: Kiểm tra title có pattern số mục không (1.1, 2.3, ...) hoặc "Bài X"
    # Nếu KHÔNG có số mục mà chỉ là text thuần → thường là lời nói đầu/giới thiệu
    has_section_number = bool(re.match(r'^\d+\.', title))
    has_bai_number = bool(re.match(r'^(Bài|BÀI|Bai|BAI|Lesson|LESSON)\s+\d+', title, re.IGNORECASE))
    
    # Nếu không có số mục + không có "Bài X" + title ngắn (<50 chars) → rất có thể là phần mở đầu
    if not has_section_number and not has_bai_number and len(title) < 50:
        # List các title thường gặp ở phần đầu document (không có chương cụ thể)
        intro_patterns = [
            r'^[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆ\s]{5,40}$',  # CHỮ IN HOA thuần
            r'^(lời|giới thiệu|phần|mở đầu|tổng quan|khái niệm)',
            r'(tổng quan|chung)',
        ]
        for pattern in intro_patterns:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return False, f"Title pattern '{pattern}' → có thể là phần mở đầu"
    
    # Kiểm tra nội dung có nhiều số trang (dấu hiệu mục lục)
    page_numbers = re.findall(r'\b\d{1,3}\s*\n', content[:800])  # Tìm số + xuống dòng
    if len(page_numbers) > 5:
        return False, f"Có {len(page_numbers)} số trang → có thể là mục lục"
    
    # Kiểm tra nội dung
    if not content or len(content) < 100:
        return False, "Nội dung quá ngắn (< 100 ký tự)"
    
    # Nếu nội dung quá dài (>20000 ký tự)
    if len(content) > 20000:
        return False, "Nội dung quá dài (> 20000 ký tự)"
    
    # Kiểm tra nội dung có ít nhất một câu hoàn chỉnh
    sentence_count = len(re.split(r'[.!?]+', content))
    if sentence_count < 2:
        return False, f"Quá ít câu ({sentence_count})"
    
    # Nếu pass hết → hợp lệ
    return True, "Hợp lệ"


def validate_section_with_ai_strict(title, content, chapter=None):
    """
    Dùng AI để PHÂN LOẠI CHẶT CHẼ section có phải nội dung thực không
    Đặc biệt chú ý: lời nói đầu, giới thiệu, mục lục, phụ lục
    """
    preview = content[:600]  # Lấy 600 ký tự để AI có đủ context
    
    validation_prompt = f"""Phân tích section này và xác định: đây có phải NỘI DUNG THỰC của giáo trình không?

TIÊU ĐỀ: {title}
CHƯƠNG: {chapter if chapter else 'Unknown'}

NỘI DUNG (600 ký tự đầu):
{preview}

---

QUY TẮC PHÂN LOẠI:
❌ LOẠI BỎ nếu là:
- Lời nói đầu, lời mở đầu, lời giới thiệu
- Mục lục (table of contents)
- Lời cảm ơn, acknowledgments  
- Phụ lục, appendix
- Tài liệu tham khảo, references
- Bài tập, câu hỏi ôn tập
- Giới thiệu chung không có nội dung kỹ thuật

✅ GIỮ LẠI nếu là:
- Nội dung kỹ thuật, lý thuyết cụ thể
- Giải thích khái niệm, định nghĩa
- Ví dụ, case study có nội dung
- Sections có số mục rõ ràng (1.1, 2.3, etc.)

TRẢ LỜI CHẶT CHẼ:
VALID - nếu là nội dung thực có thể sinh câu hỏi
INVALID - nếu là metadata/intro/appendix

Chỉ trả lời 1 từ: VALID hoặc INVALID"""
    
    try:
        response = ai_client.chat.completions.create(
            model=_cfg.QUESTION_MODEL,
            messages=[{"role": "user", "content": validation_prompt}],
            temperature=0.1,
            max_tokens=30,
            timeout=15
        )
        
        result = response.choices[0].message.content.strip().upper()
        
        if 'VALID' in result and 'INVALID' not in result:
            return True, "AI xác nhận: Nội dung thực"
        else:
            return False, "AI phát hiện: Metadata/intro/appendix"
            
    except Exception as e:
        print(f"  ⚠️  AI validation error: {e}")
        # Fallback: nếu AI fail, dùng rule-based
        # Nếu có số mục (1.1, 2.3) → likely valid
        has_section_num = bool(re.match(r'^\d+\.', title))
        if has_section_num:
            return True, "Fallback: Có số mục"
        else:
            return False, "Fallback: Không có số mục"


def validate_section_with_ai(title, content):
    """
    Dùng AI để kiểm tra section có phù hợp không
    Chỉ gọi AI nếu pass kiểm tra nhanh trước đó
    """
    # BƯỚC 1: Kiểm tra nhanh (avoid gọi AI không cần thiết)
    is_valid, reason = is_valid_section_for_qa(title, content)
    
    if not is_valid:
        print(f"  ⚠️  Section bị reject (regex): {reason}")
        return False
    
    # BƯỚC 2: Nếu pass → ai đó là một phần không rõ ràng → gọi AI confirm
    # (Rất ít khi đạt tới bước này)
    preview = content[:400]  # Lấy 400 ký tự đầu
    
    validation_prompt = f"""Kiểm tra nhanh: nội dung này có ĐỦ để sinh câu hỏi/trả lời không?

TIÊU ĐỀ: {title}

NỘI DUNG:
{preview}

---

Trả lời NGẮN (chỉ YES hoặc NO):
- YES nếu có đủ thông tin để sinh Q&A
- NO nếu là mục lục/lời cảm ơn/phụ lục/tiêu đề rỗng"""
    
    try:
        response = ai_client.chat.completions.create(
            model=_cfg.QUESTION_MODEL,
            messages=[{"role": "user", "content": validation_prompt}],
            temperature=0.1,
            max_tokens=20,
            timeout=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        
        if 'YES' in result:
            print(f"  ✅ Section valid (AI confirm)")
            return True
        else:
            print(f"  ❌ Section invalid (AI reject)")
            return False
            
    except Exception as e:
        print(f"  ⚠️  AI timeout/error: {str(e)[:40]}, dùng regex result: {is_valid}")
        return is_valid


def analyze_full_document_structure_with_ai(full_text):
    """
    🚀 BƯỚC MỚI: Cho AI phân tích TOÀN BỘ tài liệu trước khi sinh Q&A
    
    Mục đích:
    - AI đọc hết giáo trình từ đầu đến cuối (KHÔNG GIỚI HẠN)
    - Xác định TẤT CẢ các chương thực tế có trong tài liệu
    - Trả về danh sách đầy đủ chapters để sinh Q&A

    Returns:
        dict: {
            'total_chapters': int,
            'chapter_list': ['Chương 1', 'Chương 2', ...],
            'chapter_details': {
                'Chương 1': {'title': '...', 'sections': [...], 'summary': '...'},
                ...
            },
            'full_summary': str  # Tóm tắt toàn bộ tài liệu
        }
    """
    print("\n" + "="*80)
    print("🚀 BƯỚC MỚI: AI PHÂN TÍCH TOÀN BỘ GIÁO TRÌNH (KHÔNG GIỚI HẠN)")
    print("="*80)
    
    # Tính toán thống kê
    total_chars = len(full_text)
    total_words = len(full_text.split())
    estimated_tokens = int(total_words * 1.3)
    
    print(f"\n📊 Thông tin tài liệu:")
    print(f"   - Tổng ký tự: {total_chars:,}")
    print(f"   - Tổng từ: {total_words:,}")
    print(f"   - Ước tính tokens: ~{estimated_tokens:,}")
    print(f"   - Chi phí ước tính: ~${estimated_tokens * 0.000000075:.4f} (input)")
    
    print(f"\n⏳ Đang gửi TOÀN BỘ tài liệu cho AI phân tích...")
    print(f"   (Quá trình này có thể mất 30-60 giây tùy kích thước tài liệu)")
    
    analysis_prompt = f"""Bạn là chuyên gia phân tích tài liệu giáo trình. Hãy đọc TOÀN BỘ tài liệu dưới đây và phân tích cấu trúc.

📚 TOÀN BỘ TÀI LIỆU GIÁO TRÌNH:
--- BẮT ĐẦU TÀI LIỆU ---
{full_text}
--- KẾT THÚC TÀI LIỆU ---

🎯 YÊU CẦU PHÂN TÍCH:

1. XÁC ĐỊNH TẤT CẢ CÁC CHƯƠNG:
   - Đọc từ đầu đến cuối tài liệu
   - Liệt kê TẤT CẢ chương (dù là La Mã I, II, III... hoặc số 1, 2, 3...)
   - Mỗi chương ghi rõ: số chương, tên chương, các mục con quan trọng

2. TẠO DANH SÁCH CHƯƠNG:
   Format: Chương 1, Chương 2, Chương 3...
   (Nếu dùng La Mã thì chuyển sang số: I→1, II→2, III→3...)

3. TÓM TẮT MỖI CHƯƠNG (2-3 câu):
   - Nội dung chính của chương
   - Các khái niệm/chủ đề quan trọng

4. TÓM TẮT TOÀN BỘ TÀI LIỆU (1 đoạn):
   - Môn học/lĩnh vực gì?
   - Phạm vi kiến thức?
   - Mục đích giảng dạy?

📋 TRẢ LỜI THEO FORMAT JSON SAU (CHẶT CHẼ):
{{
    "total_chapters": <số chương>,
    "chapter_list": ["Chương 1", "Chương 2", "Chương 3", ...],
    "chapter_details": {{
        "Chương 1": {{
            "title": "Tên chương 1",
            "main_sections": ["1.1 Mục 1", "1.2 Mục 2", ...],
            "summary": "Tóm tắt nội dung chương 1..."
        }},
        "Chương 2": {{
            "title": "Tên chương 2",
            "main_sections": ["2.1 Mục 1", "2.2 Mục 2", ...],
            "summary": "Tóm tắt nội dung chương 2..."
        }},
        ...
    }},
    "document_summary": "Tóm tắt toàn bộ tài liệu...",
    "subject": "Tên môn học/lĩnh vực",
    "total_sections": <tổng số mục con trong tất cả chương>
}}

⚠️ QUAN TRỌNG:
- PHẢI đọc HẾT tài liệu, KHÔNG BỎ SÓT chương nào
- Nếu có 10 chương thì PHẢI liệt kê đủ 10
- Nếu có 20 chương thì PHẢI liệt kê đủ 20
- KHÔNG giới hạn số chương

Trả lời (CHỈ JSON, không giải thích thêm):"""

    try:
        print(f"   📡 Sending request to {_cfg.ANSWER_MODEL}...")
        
        response = ai_client.chat.completions.create(
            model=_cfg.ANSWER_MODEL,  # Dùng Gemini 2.0 Flash - rẻ và context window lớn
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.3,  # Low temp để phân tích chính xác
            max_tokens=8000,  # Đủ lớn cho phân tích chi tiết
            timeout=120  # 2 phút timeout cho documents lớn
        )
        
        raw_response = response.choices[0].message.content.strip()
        
        print(f"\n✅ AI đã phân tích xong!")
        print(f"   Response length: {len(raw_response)} chars")
        
        # Parse JSON response
        # Loại bỏ markdown code blocks nếu có
        json_text = raw_response
        if '```json' in json_text:
            json_text = json_text.split('```json')[1].split('```')[0].strip()
        elif '```' in json_text:
            json_text = json_text.split('```')[1].split('```')[0].strip()
        
        analysis_result = json.loads(json_text)
        
        # Validate kết quả
        total_chapters = analysis_result.get('total_chapters', 0)
        chapter_list = analysis_result.get('chapter_list', [])
        
        print(f"\n📊 KẾT QUẢ PHÂN TÍCH:")
        print(f"   ✅ Tổng số chương: {total_chapters}")
        print(f"   ✅ Danh sách: {', '.join(chapter_list[:10])}")
        if len(chapter_list) > 10:
            print(f"      ... và {len(chapter_list) - 10} chương nữa")
        print(f"   ✅ Môn học: {analysis_result.get('subject', 'N/A')}")
        print(f"   ✅ Tổng sections: {analysis_result.get('total_sections', 'N/A')}")
        
        # In details của 3 chương đầu
        print(f"\n📚 Chi tiết một số chương:")
        chapter_details = analysis_result.get('chapter_details', {})
        for i, ch in enumerate(chapter_list[:3]):
            if ch in chapter_details:
                detail = chapter_details[ch]
                print(f"\n   {ch}: {detail.get('title', 'N/A')}")
                sections = detail.get('main_sections', [])
                print(f"      Sections: {', '.join(sections[:5])}")
                if len(sections) > 5:
                    print(f"      ... và {len(sections) - 5} mục nữa")
        
        if len(chapter_list) > 3:
            print(f"\n   ... và {len(chapter_list) - 3} chương nữa")
        
        print(f"\n✅✅ HOÀN TẤT PHÂN TÍCH TOÀN BỘ TÀI LIỆU!")
        print(f"   → AI đã đọc {total_words:,} từ và xác định {total_chapters} chương")
        print(f"   → Giờ sẽ sinh câu hỏi cho TẤT CẢ {total_chapters} chương này")
        
        # Lưu lại số chương AI phát hiện để validation sau này
        analysis_result['ai_detected_chapters'] = total_chapters
        
        return analysis_result
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Lỗi parse JSON: {e}")
        print(f"   Raw response preview: {raw_response[:500]}")
        
        # Fallback: Thử extract thông tin cơ bản
        print(f"\n⚠️  Fallback: Dùng regex extract chapters...")
        return fallback_extract_chapters(full_text)
        
    except Exception as e:
        print(f"\n❌ Lỗi khi phân tích với AI: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Fallback
        print(f"\n⚠️  Fallback: Dùng regex extract chapters...")
        return fallback_extract_chapters(full_text)


def fallback_extract_chapters(text):
    """
    Fallback: Nếu AI fail, dùng regex để extract chapters
    """
    print(f"\n🔧 FALLBACK MODE: Regex extraction")
    
    # Tìm tất cả patterns chapter
    chapter_patterns = [
        r'Chương\s+(\d+)',
        r'CHƯƠNG\s+(\d+)',
        r'Phần\s+([IVX]+)',
        r'PHẦN\s+([IVX]+)',
        r'Chapter\s+(\d+)',
    ]
    
    chapters_found = set()
    
    for pattern in chapter_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Chuyển La Mã sang số
            if re.match(r'[IVX]+', match):
                roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 
                            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
                            'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
                            'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20}
                num = roman_map.get(match, 0)
                if num > 0:
                    chapters_found.add(num)
            else:
                try:
                    chapters_found.add(int(match))
                except:
                    pass
    
    if chapters_found:
        chapter_nums = sorted(list(chapters_found))
        total_chapters = len(chapter_nums)
        chapter_list = [f"Chương {i}" for i in chapter_nums]
        
        print(f"   ✅ Found {total_chapters} chapters: {chapter_list}")
        
        return {
            'total_chapters': total_chapters,
            'chapter_list': chapter_list,
            'chapter_details': {ch: {'title': ch, 'main_sections': [], 'summary': ''} for ch in chapter_list},
            'document_summary': 'Phân tích tự động từ regex',
            'subject': 'Unknown',
            'total_sections': 0
        }
    else:
        # Không tìm thấy gì
        print(f"   ❌ Không tìm thấy chapters!")
        return {
            'total_chapters': 1,
            'chapter_list': ['Chương 1'],
            'chapter_details': {'Chương 1': {'title': 'Toàn bộ tài liệu', 'main_sections': [], 'summary': ''}},
            'document_summary': 'Không xác định được cấu trúc',
            'subject': 'Unknown',
            'total_sections': 0
        }


def create_chapter_rotation(num_chapters, question_count):
    """
    Tạo danh sách chapters xoay vòng để tránh lặp chương LIÊN TIẾP
    
    Logic:
    - Nếu question_count <= num_chapters: shuffle và lấy random chapters (không theo thứ tự 0,1,2...)
    - Nếu question_count > num_chapters: shuffle nhiều lần nhưng đảm bảo NO liên tiếp
    
    QUAN TRỌNG: Luôn shuffle để chapters được phân bố đều, không bias về chương đầu
    """
    if num_chapters <= 1:
        # Chỉ có 1 chapter (hoặc 0) - trả về list lặp chapter 0
        return [0] * question_count

    if question_count <= num_chapters:
        # Không cần lặp - nhưng PHẢI shuffle để random
        chapters = list(range(num_chapters))
        random.shuffle(chapters)  # CRITICAL FIX: shuffle để không bias chapter đầu
        return chapters[:question_count]
    
    # Cần lặp - phải shuffle thông minh
    result = []
    remaining = question_count
    used_last = None  # Track chapter đã dùng cuối cùng
    
    while remaining > 0:
        # Tạo danh sách chapters có thể dùng (TRỪ chapter cuối cùng để tránh liên tiếp)
        available = list(range(num_chapters))
        if used_last is not None and num_chapters > 1 and used_last in available:
            available.remove(used_last)
        
        if not available:
            # Safety: nếu available rỗng thì dùng tất cả chapters
            available = list(range(num_chapters))
        
        # Shuffle danh sách
        random.shuffle(available)
        
        # Thêm vào result
        for chapter_idx in available:
            if remaining <= 0:
                break
            result.append(chapter_idx)
            used_last = chapter_idx
            remaining -= 1
    
    return result[:question_count]


def create_content_chunks_for_questions(text, question_count, page_boundaries=None):
    """
    Chia document thành chunks để sinh câu hỏi
    
    CHIẾN LƯỢC MỚI:
    1. AI phân tích THỰC SỰ tài liệu có bao nhiêu chương
    2. Tách document thành chunks (mỗi chunk = 1 chương + context)
    3. Đảm bảo KHÔNG lặp chương nếu có thể
    4. Nếu phải lặp: shuffle danh sách chapters
    
    Returns: List of chunk dictionaries
    """
    print("\n" + "="*70)
    print("BƯỚC 1: TỰ ĐỘNG DETECT CẤU TRÚC DOCUMENT")
    print("="*70)
    
    # Detect có sections hay không
    has_sections, _ = detect_document_structure(text)
    
    print("\n" + "="*70)
    print("BƯỚC 2: AI PHÂN TÍCH SỐ CHƯƠNG THỰC TẾ")
    print("="*70)
    
    num_chapters, chapter_names = analyze_chapters_with_ai(text)
    
    # CRITICAL FIX: Verify với sections thật
    # AI có thể phát hiện sai, hãy cross-check với sections đã extract
    print(f"\n🔍 Verifying chapter detection...")
    print(f"   AI detected: {num_chapters} chapters - {chapter_names}")
    
    # Lấy danh sách chapters thực tế từ document structure detection
    actual_sections = split_document_into_sections(text[:50000], page_boundaries=page_boundaries)  # Sample 50k chars
    actual_chapters = set(s.get('chapter') for s in actual_sections if s.get('chapter') and s.get('chapter') not in ('Unknown', 'Tài liệu'))
    
    if actual_chapters:
        # For "Chương X" format: extract numbers and find max
        actual_chuong = [ch for ch in actual_chapters if 'Chương' in str(ch)]
        if actual_chuong:
            actual_nums = sorted([int(re.search(r'\d+', ch).group()) for ch in actual_chuong if re.search(r'\d+', ch)])
            max_chapter = max(actual_nums) if actual_nums else num_chapters
            
            if max_chapter != num_chapters:
                print(f"   ⚠️  AI mismatch! Actual max chapter: {max_chapter}")
                print(f"   → Correcting: {num_chapters} → {max_chapter}")
                num_chapters = max_chapter
                chapter_names = [f"Chương {i+1}" for i in range(num_chapters)]
                print(f"   ✅ Corrected: {chapter_names}")
        else:
            # Non-"Chương" chapters (e.g. "Chủ đề: X") → use actual count
            actual_count = len(actual_chapters)
            if actual_count > num_chapters:
                print(f"   ⚠️  Found {actual_count} topic-chapters (not 'Chương' format)")
                num_chapters = actual_count
                chapter_names = sorted(list(actual_chapters))
                print(f"   ✅ Using topic chapters: {chapter_names[:5]}...")
    
    print(f"   Final: {num_chapters} chapters")
    
    print("\n" + "="*70)
    print("BƯỚC 3: TẠO DANH SÁCH XOAY VÒNG (KHÔNG LẶP)")
    print("="*70)
    
    # Tạo chapter rotation: trả lại danh sách chapter indices (0-indexed)
    chapter_rotation = create_chapter_rotation(num_chapters, question_count)
    
    print(f"  Danh sách câu hỏi theo chương:")
    for q_idx in range(min(question_count, 10)):  # In 10 cái đầu tiên
        chapter_idx = chapter_rotation[q_idx]
        print(f"    Câu {q_idx+1}: {chapter_names[chapter_idx]}")
    
    if question_count > 10:
        print(f"    ... ({question_count - 10} câu tiếp theo)")
    
    # DEBUG: Xem tất cả chapters được dùng
    rotation_chapters = [chapter_names[idx] for idx in chapter_rotation]
    unique_used = set(rotation_chapters)
    print(f"\n  📊 Rotation coverage:")
    print(f"     Total chapters: {num_chapters}")
    print(f"     Chapters used: {len(unique_used)} - {sorted(unique_used)}")
    if len(unique_used) < num_chapters:
        unused = set(chapter_names) - unique_used
        print(f"     ⚠️  UNUSED chapters: {unused}")
    
    # DEBUG: In chi tiết rotation
    print(f"\n  📋 Chi tiết rotation:")
    for idx, ch_idx in enumerate(chapter_rotation):
        print(f"     Câu {idx+1} → {chapter_names[ch_idx]}")
    
    print(f"\n✅ Xác định {question_count} câu hỏi từ {num_chapters} chương")
    print(f"   Chiến lược: Full document + focus indicator")
    
    print("\n" + "="*70)
    print("BƯỚC 4: TRÍCH XUẤT TOÀN BỘ SECTIONS")
    print("="*70)
    
    # DEBUG: Kiểm tra document length
    print(f"\n📊 DOCUMENT INFO:")
    print(f"   - Text length: {len(text):,} chars")
    print(f"   - Text length: {len(text.split()):,} words")
    print(f"   - Estimated pages: ~{len(text) // 3000} pages (assuming 3000 chars/page)")
    
    # CRITICAL: Lấy TOÀN BỘ sections trong document (không giới hạn)
    all_sections_full = split_document_into_sections(text, page_boundaries=page_boundaries)
    print(f"\n� TOTAL PARSED: {len(all_sections_full)} sections")
    
    # DEBUG: Thống kê ban đầu
    initial_chapter_count = {}
    for sec in all_sections_full:
        ch = sec.get('chapter', 'Unknown')
        initial_chapter_count[ch] = initial_chapter_count.get(ch, 0) + 1
    
    print(f"\n📊 Chapters trước khi validation:")
    for ch in sorted(initial_chapter_count.keys()):
        print(f"   {ch}: {initial_chapter_count[ch]} sections")
    
    # Lọc sections hợp lệ - RELAXED MODE (giữ nhiều sections hơn)
    # ⚠️ NẾU CẦN BỎ VALIDATION ĐỂ GIỮ TẤT CẢ SECTIONS:
    #    valid_sections = all_sections_full  # Uncomment dòng này
    #    print(f"\n⚠️ BYPASS VALIDATION - Giữ tất cả {len(valid_sections)} sections")
    # Nếu không, dùng validation thông thường:
    
    valid_sections = []
    rejected_sections = []
    
    # 🚨 BỎ VALIDATION - GIỮ TẤT CẢ SECTIONS ĐỂ ĐỌC FULL GIÁO TRÌNH
    print(f"\n🚨 BYPASS VALIDATION MODE - Giữ tất cả sections có số mục")
    
    for sec in all_sections_full:
        title = sec['title']
        
        # CHỈ lọc sections có số mục rõ ràng (1.1, 2.3) hoặc tiêu đề chương
        # KHÔNG dùng is_valid_section_for_qa() nữa
        has_section_number = bool(re.match(r'^\d+\.\d+', title))
        is_chapter_header = bool(re.match(r'^(Chương|CHƯƠNG|Phần|PHẦN)', title, re.IGNORECASE))
        is_bai_header = bool(re.match(r'^(Bài|BÀI|Bai|BAI|Lesson|LESSON)\s+\d+', title, re.IGNORECASE))
        is_fallback_chunk = bool(re.match(r'^(Đoạn|Trang) \d+', title))
        
        if has_section_number or is_chapter_header or is_bai_header or is_fallback_chunk:
            valid_sections.append(sec)
    
    # If STILL no valid sections, use ALL sections as-is
    if not valid_sections and all_sections_full:
        print(f"  ⚠️ No sections matched filters, using ALL {len(all_sections_full)} sections")
        valid_sections = all_sections_full
    
    print(f"✅ Kết quả: {len(valid_sections)}/{len(all_sections_full)} sections")
    
    rejected_sections = []
    
    # DEBUG: Thống kê SAU bypass
    after_chapter_count = {}
    for sec in valid_sections:
        ch = sec.get('chapter', 'Unknown')
        after_chapter_count[ch] = after_chapter_count.get(ch, 0) + 1
    
    print(f"\n📊 Chapters SAU bypass:")
    sorted_after = sorted([ch for ch in after_chapter_count.keys() if ch != 'Unknown'])
    for ch in sorted_after:
        print(f"   {ch}: {after_chapter_count[ch]} sections")
    if 'Unknown' in after_chapter_count:
        print(f"   Unknown: {after_chapter_count['Unknown']} sections")
    
    # Report thành công
    total_chapters = len([ch for ch in after_chapter_count.keys() if ch != 'Unknown'])
    if total_chapters >= 3:
        print(f"\n✅✅ THÀNH CÔNG: Phát hiện {total_chapters} chương!")
        print(f"   → AI sẽ xem TOÀN BỘ {total_chapters} chương để sinh câu hỏi")
    else:
        print(f"\n⚠️⚠️  VẪN CHỈ PHÁT HIỆN {total_chapters} CHƯƠNG!")
        print(f"   → PDF có thể thực sự chỉ có {total_chapters} chương hoặc bị cắt ngắn")
        print(f"   → Kiểm tra lại PDF gốc hoặc gửi log parse cho dev")
    
    # Nhóm sections theo chapter
    sections_by_chapter = {}
    for sec in valid_sections:
        ch = sec.get('chapter', 'Unknown')
        if ch not in sections_by_chapter:
            sections_by_chapter[ch] = []
        sections_by_chapter[ch].append(sec)
    
    print(f"\n📊 Phân bố sections theo chapter:")
    for ch in sorted(sections_by_chapter.keys()):
        print(f"   {ch}: {len(sections_by_chapter[ch])} sections")
    
    # WARNING: Nếu chỉ có ít chapters → document bị cắt ngắn!
    if len(sections_by_chapter) < 3:
        print(f"\n⚠️  CẢNH BÁO: Chỉ phát hiện {len(sections_by_chapter)} chapters!")
        print(f"   → Nếu giáo trình có nhiều chương hơn, có thể document bị cắt ngắn.")
        print(f"   → Nên UPLOAD LẠI PDF đầy đủ để đảm bảo chất lượng!")
    elif len(sections_by_chapter) >= 10:
        print(f"\n✅ Tốt! Phát hiện {len(sections_by_chapter)} chương - Document đầy đủ!")
        print(f"   → AI sẽ xem TOÀN BỘ tài liệu để sinh câu hỏi chất lượng cao")
    
    print("\n" + "="*70)
    print("BƯỚC 5: PHÂN BỔ QUESTIONS - ROUND ROBIN (ĐỀU TẤT CẢ CHƯƠNG)")
    print("="*70)
    print(f"📚 Document có {len(sections_by_chapter)} chương sẽ được phân bổ đều")
    
    chunks = []
    
    if not valid_sections:
        print("❌ KHÔNG CÓ SECTIONS HỢP LỆ!")
        return []
    
    # CHIẾN LƯỢC MỚI: Round-robin để đảm bảo mỗi câu từ chương khác nhau
    # Ví dụ: 6 chapters, 10 câu → C1, C2, C3, C4, C5, C6, C1, C2, C3, C4
    
    # Get sorted list of chapters
    chapter_list = sorted(sections_by_chapter.keys())
    num_chapters = len(chapter_list)
    
    print(f"\n📊 ROUND-ROBIN ALLOCATION:")
    print(f"   - 📖 Tổng chapters có sẵn: {num_chapters}")
    print(f"   - Danh sách: {', '.join(chapter_list)}")
    print(f"   - ❓ Tổng câu hỏi: {question_count}")
    
    if question_count <= num_chapters:
        print(f"   - Chiến lược: 1 câu/chapter, cover {question_count} chapters đầu")
    else:
        cycles = question_count // num_chapters
        remainder = question_count % num_chapters
        print(f"   - Chiến lược: {cycles} vòng đầy đủ + {remainder} câu bổ sung")
        print(f"   - Mỗi chapter: {cycles}-{cycles+1} câu")
    
    # Tạo rotation list cho questions
    chapter_rotation = []
    for i in range(question_count):
        chapter_idx = i % num_chapters
        chapter_rotation.append(chapter_list[chapter_idx])
    
    # Shuffle để không lấy tuần tự từ trên xuống
    # NHƯNG đảm bảo không có 2 câu liên tiếp cùng chapter
    random.shuffle(chapter_rotation)
    
    # Fix: Nếu có 2 câu liên tiếp cùng chapter → swap
    for i in range(len(chapter_rotation) - 1):
        if chapter_rotation[i] == chapter_rotation[i+1]:
            # Tìm vị trí khác để swap
            for j in range(i+2, len(chapter_rotation)):
                if chapter_rotation[j] != chapter_rotation[i] and (j == len(chapter_rotation)-1 or chapter_rotation[j] != chapter_rotation[j+1]):
                    # Swap
                    chapter_rotation[i+1], chapter_rotation[j] = chapter_rotation[j], chapter_rotation[i+1]
                    break
    
    print(f"\n📋 Chi tiết phân bổ:")
    for idx, ch in enumerate(chapter_rotation):
        print(f"   Câu {idx+1}: {ch}")
    
    # Count questions per chapter
    questions_per_chapter = {}
    for ch in chapter_rotation:
        questions_per_chapter[ch] = questions_per_chapter.get(ch, 0) + 1
    
    print(f"\n📊 Tổng kết phân bổ:")
    for ch in sorted(questions_per_chapter.keys()):
        print(f"   {ch}: {questions_per_chapter[ch]} câu từ {len(sections_by_chapter[ch])} sections")
    
    # Tạo chunks theo rotation
    question_idx = 0
    for ch in chapter_rotation:
        chapter_sections = sections_by_chapter[ch]
        
        # Random chọn 1 section từ chapter này
        selected_sec = random.choice(chapter_sections)
        
        # Tạo chunk với full document + focus vào section cụ thể
        preamble = f"""\
[🎯 HƯỚNG DẪN: Sinh câu hỏi về phần sau]

Yêu cầu:
- Sử dụng TOÀN BỘ nội dung giáo trình dưới đây
- Tập trung vào: {ch} - {selected_sec['title']}
- Tạo câu hỏi và trả lời chất lượng cao dựa trên nội dung section này

========== NỘI DUNG GIÁO TRÌNH ĐẦY ĐỦ ==========

"""
        
        chunk_content = preamble + text
        
        chunks.append({
            'index': question_idx,
            'content': chunk_content,
            'title': f"Câu {question_idx+1}: {selected_sec['title']}",
            'chapter': ch,
            'section_title': selected_sec['title'],
            'section_content': selected_sec['content'],
            'section_num': selected_sec['title'].split()[0] if selected_sec['title'] else None,
            'has_sections': has_sections,
            'char_count': len(chunk_content),
            'page_num': selected_sec.get('page_num'),
        })
        
        print(f"  ✓ Câu {question_idx+1}: {ch} - {selected_sec['title'][:50]}")
        question_idx += 1
    
    print(f"\n✅ Đã tạo {len(chunks)} chunks covering {len(set(chapter_rotation))} unique chapters")
    
    print(f"\n✅ Hoàn tất: {question_count} chunks, từ {num_chapters} chương")
    print(f"   Cấu trúc: {'Có mục' if has_sections else 'Chỉ chương'}")
    
    return chunks

# ══════════════════════════════════════════════════════════════════════════════
# NEW 3-AGENT PIPELINE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

# Tập từ dừng tiếng Việt — loại bỏ khi tính độ tương đồng văn bản
# (các từ phổ biến không mang nghĩa phân biệt: "của", "và", "là"...)
_STOP_VI = frozenset({
    'của', 'và', 'các', 'trong', 'được', 'với', 'cho', 'từ', 'này', 'như', 'để',
    'theo', 'một', 'những', 'đến', 'việc', 'trên', 'hay', 'có', 'khi', 'hoặc',
    'là', 'sẽ', 'tại', 'nên', 'mà', 'bằng', 'đã', 'đang', 'vào', 'ra',
    'bởi', 'về', 'giữa', 'nếu', 'sau', 'trước', 'thì', 'đây', 'đó', 'cũng', 'không',
    'phần', 'bài', 'còn', 'rất', 'nhiều', 'hơn', 'nhất', 'do', 'vì', 'mỗi',
})


def _a3_word_overlap(text_a, text_b):
    """Tính tỉ lệ từ trùng lặp giữa text_a và text_b (loại stopword).
    Dùng để đo câu hỏi có bám sát nội dung section không.
    Trả về float 0.0–1.0 (1.0 = tất cả từ của text_a đều có trong text_b).
    """
    if not text_a or not text_b:
        return 0.0
    words_a = set(re.findall(r'\w{2,}', text_a.lower())) - _STOP_VI  # tập từ của text_a
    words_b = set(re.findall(r'\w{2,}', text_b.lower())) - _STOP_VI  # tập từ của text_b
    if not words_a:
        return 0.0
    return round(len(words_a & words_b) / len(words_a), 4)  # tỉ lệ từ a có trong b


def _normalize_math_text(text: str) -> str:
    """Chuẩn hóa ký hiệu toán học/hóa học sang ASCII để so sánh n-gram công bằng.
    Ví dụ: H₂SO₄ → H2SO4, x² → x^2, π → pi, α → alpha.
    Dùng trước khi tính groundedness để tránh false-negative với tài liệu STEM.
    """
    if not text:
        return text

    # Subscript digits: ₀₁₂₃₄₅₆₇₈₉ → 0123456789
    _sub_map = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
    text = text.translate(_sub_map)

    # Superscript digits/signs: ⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ → 0123456789+-
    _sup_map = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻', '0123456789+-')
    text = text.translate(_sup_map)

    # Common superscripts: ² ³ (U+00B2, U+00B3) — rất phổ biến trong toán/hóa
    text = text.replace('²', '2').replace('³', '3')

    # Greek letters → Latin equivalents (thường dùng trong toán/vật lý)
    _greek = {
        'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'ε': 'epsilon',
        'ζ': 'zeta', 'η': 'eta', 'θ': 'theta', 'ι': 'iota', 'κ': 'kappa',
        'λ': 'lambda', 'μ': 'mu', 'ν': 'nu', 'ξ': 'xi', 'ο': 'omicron',
        'π': 'pi', 'ρ': 'rho', 'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon',
        'φ': 'phi', 'χ': 'chi', 'ψ': 'psi', 'ω': 'omega',
        'Α': 'Alpha', 'Β': 'Beta', 'Γ': 'Gamma', 'Δ': 'Delta', 'Ε': 'Epsilon',
        'Θ': 'Theta', 'Λ': 'Lambda', 'Μ': 'Mu', 'Π': 'Pi', 'Σ': 'Sigma',
        'Φ': 'Phi', 'Ψ': 'Psi', 'Ω': 'Omega',
    }
    for greek, latin in _greek.items():
        text = text.replace(greek, latin)

    # Math operators → ASCII
    text = (text
        .replace('∞', 'infinity').replace('∑', 'sum').replace('∫', 'integral')
        .replace('∂', 'd').replace('∇', 'nabla').replace('√', 'sqrt')
        .replace('≤', '<=').replace('≥', '>=').replace('≠', '!=')
        .replace('≈', '~').replace('→', '->').replace('⇒', '=>')
        .replace('⇌', '<->').replace('±', '+-').replace('×', '*')
        .replace('÷', '/').replace('·', '*').replace('∝', 'prop')
        .replace('∈', 'in').replace('∉', 'not_in').replace('∀', 'for_all')
        .replace('∃', 'exists').replace('∅', 'empty')
        .replace('°', 'deg').replace('µ', 'micro').replace('Å', 'A')
    )
    return text


def _a3_ngram_groundedness(answer, source_content):
    """Đo mức độ đáp án lấy từ tài liệu bằng n-gram overlap (tương tự BLEU).
    Kết hợp unigram + bigram + trigram + 4-gram → điểm tổng hợp.
    Áp dụng normalize toán học để không phạt oan tài liệu STEM.
    Trả về float 0.0–1.0 (càng cao = đáp án càng bám sát tài liệu gốc).
    """
    if not answer or not source_content:
        return 0.0

    # Normalize ký hiệu toán/hóa trước khi tính n-gram
    answer_norm  = _normalize_math_text(answer)
    source_norm  = _normalize_math_text(source_content)

    def _tokens(text):
        # Tách từ ≥2 ký tự, bỏ stopword
        return [w for w in re.findall(r'\w{2,}', text.lower()) if w not in _STOP_VI]

    def _ngram_set(tokens, n):
        # Tạo tập n-gram từ danh sách token
        return set(zip(*[tokens[i:] for i in range(n)])) if len(tokens) >= n else set()

    tok_a = _tokens(answer_norm)        # token của đáp án (đã normalize)
    tok_s = _tokens(source_norm)        # token của tài liệu (đã normalize)

    # Tính overlap từng mức n-gram
    uni  = len(set(tok_a) & set(tok_s)) / max(len(set(tok_a)), 1)  # 1-gram
    bi_a, bi_s   = _ngram_set(tok_a, 2), _ngram_set(tok_s, 2)
    bi   = len(bi_a & bi_s)   / max(len(bi_a), 1)                  # 2-gram
    tri_a, tri_s = _ngram_set(tok_a, 3), _ngram_set(tok_s, 3)
    tri  = len(tri_a & tri_s) / max(len(tri_a), 1)                 # 3-gram
    fg_a, fg_s   = _ngram_set(tok_a, 4), _ngram_set(tok_s, 4)
    four = len(fg_a & fg_s)   / max(len(fg_a), 1)                  # 4-gram

    # Trọng số nặng hơn cho n-gram dài (bi/tri/4) vì tiếng Việt ghép từ nhiều
    score = uni * 0.20 + bi * 0.30 + tri * 0.30 + four * 0.20
    return round(min(score, 1.0), 4)


def _a3_concept_overlap(answer, source_content):
    """Đo mức độ đáp án dùng khái niệm/thuật ngữ từ tài liệu — dành cho Bloom 5-6.
    Đo theo hướng PRECISION từ đáp án: % từ có nghĩa của đáp án có trong key terms tài liệu.
    (Ngược lại recall từ source sẽ rất thấp vì source dài hàng ngàn từ, answer ngắn)
    Trả về float 0.0–1.0.
    """
    if not answer or not source_content:
        return 0.0

    # Trích key terms từ tài liệu: từ ≥3 ký tự, không stopword, xuất hiện ≥2 lần
    src_tokens = re.findall(r'\w{3,}', source_content.lower())
    src_freq = Counter(t for t in src_tokens if t not in _STOP_VI)
    key_terms = {t for t, freq in src_freq.items() if freq >= 2}

    if not key_terms:
        # Fallback: tất cả từ ≥4 ký tự không stopword
        key_terms = {t for t in src_tokens if len(t) >= 4 and t not in _STOP_VI}

    if not key_terms:
        return 0.5  # không xác định được → trung lập

    # Precision từ answer: % từ có nghĩa của đáp án có xuất hiện trong key_terms tài liệu
    ans_meaningful = [t for t in re.findall(r'\w{3,}', answer.lower()) if t not in _STOP_VI]
    if not ans_meaningful:
        return 0.0
    matched = sum(1 for t in ans_meaningful if t in key_terms)
    return round(matched / len(ans_meaningful), 4)


def _is_english_content(text: str) -> bool:
    """Phát hiện nhanh xem đoạn text có phải tiếng Anh không (không cần thư viện).
    Dựa vào tỉ lệ ký tự Vietnamese Unicode (U+1E00–U+1EFF): nếu gần như không có
    thì coi là tiếng Anh. Đủ nhanh để gọi inline.
    """
    if not text or len(text) < 30:
        return False
    sample = text[:500]
    total_alpha = sum(1 for c in sample if c.isalpha())
    if total_alpha == 0:
        return False
    viet_chars = sum(1 for c in sample if '\u1e00' <= c <= '\u1eff')
    # Nếu ký tự Vietnamese < 1% tổng alpha → tiếng Anh
    return (viet_chars / total_alpha) < 0.01


def _effective_bloom_ceiling(bloom_ceiling: int, bloom_num: int, content_len: int) -> int:
    """Ceiling thực tế sau khi nới cho Bloom cao.

    Câu B4–B6 có thể sinh từ nội dung thấp hơn (phân tích/đánh giá/đề xuất dựa trên kiến thức
    có sẵn). AI ceiling hay underestimate, đặc biệt B5–B6 tiếng Việt.
    """
    if bloom_ceiling is None:
        return 6
    if content_len <= 300:
        # Đoạn ngắn: cho phép lệch 1 bậc với B4+, còn B1–B3 giữ strict
        if bloom_num >= 4:
            return min(6, bloom_ceiling + 1)
        return bloom_ceiling
    boost = {4: 1, 5: 2, 6: 2}.get(bloom_num, 0)
    return min(6, bloom_ceiling + boost)


def _get_section_bloom_ceiling(section_content: str, section_title: str) -> int:
    """Dùng AI để xác định cấp độ Bloom CAO NHẤT mà nội dung section này có thể hỗ trợ.
    Trả về: int 1–6.
    - Section ngắn (≤300 chars): dùng classify_bloom_exact() → ceiling = Bloom chính xác của đoạn.
    - Section dài (>300 chars): dùng prompt ceiling như cũ.
    - Fallback về heuristic keyword nếu AI lỗi/timeout.
    """
    content = section_content.strip()
    if len(content) < 50:
        return 1  # Quá ngắn → chỉ hỗ trợ Bloom 1

    # Section ngắn → dùng classify_bloom_exact: biết chính xác đoạn này thuộc Bloom mấy
    # ceiling = đúng level đó (không cần hỏi "tối đa bao nhiêu")
    if len(content) <= 300:
        level, reason = classify_bloom_exact(content)
        print(f"    🔬 Section ngắn → classify_exact → Bloom {level} ({reason[:40]})")
        return level

    preview = section_content[:900]
    prompt = (
        f"Đọc đoạn tài liệu sau và xác định cấp Bloom CAO NHẤT của CÂU HỎI có thể đặt ra từ nội dung này.\n\n"
        f"Tiêu đề mục: {section_title}\n"
        f"Nội dung:\n{preview}\n\n"
        f"Thang Bloom (1→6) — mức câu hỏi có thể đặt ra:\n"
        f"1=Nhớ: chỉ hỏi liệt kê/định nghĩa (nội dung chỉ có danh sách/thuật ngữ)\n"
        f"2=Hiểu: có thể hỏi giải thích/mô tả (nội dung có mô tả khái niệm)\n"
        f"3=Vận dụng: có thể hỏi áp dụng/thực hiện (nội dung có quy trình/công thức)\n"
        f"4=Phân tích: có thể hỏi so sánh/phân loại/nguyên nhân (nội dung đủ phong phú)\n"
        f"5=Đánh giá: có thể hỏi nhận xét/biện luận/lựa chọn giải pháp (nội dung có nhiều góc độ)\n"
        f"6=Sáng tạo: có thể hỏi thiết kế/đề xuất/xây dựng mô hình (nội dung đủ để người học sáng tạo)\n\n"
        f"Lưu ý quan trọng:\n"
        f"- Nội dung không cần chứa từ 'thiết kế' hay 'đề xuất' để đạt Bloom 6; chỉ cần đủ kiến thức để người học tự sáng tạo.\n"
        f"- Nội dung dài, đa chiều, nhiều khái niệm liên kết → thường đạt Bloom 5-6.\n"
        f"- Chỉ cho điểm 1 nếu nội dung thực sự chỉ là danh sách/định nghĩa đơn thuần.\n\n"
        f"Trả lời CHỈ 1 số từ 1 đến 6:"
    )

    try:
        response = ai_client.chat.completions.create(
            model=_cfg.QUESTION_MODEL,
            messages=[
                {"role": "system", "content":
                 "Reply with ONLY a single digit (1-6). No text, no explanation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=5,
            timeout=12,
        )
        result = response.choices[0].message.content.strip()
        m = re.search(r'[1-6]', result)
        if m:
            return int(m.group())
    except Exception as e:
        print(f"    ⚠️ Bloom ceiling AI lỗi: {str(e)[:60]}")

    # Fallback heuristic keyword-based
    c = section_content.lower()
    clen = len(section_content.strip())
    # Bloom 5-6: không yêu cầu từ khóa đặc biệt — nội dung đủ dài và phong phú là đủ
    if any(w in c for w in ['đề xuất giải pháp', 'thiết kế hệ thống', 'xây dựng mô hình', 'phát triển giải pháp']):
        return 6
    if any(w in c for w in ['ưu điểm', 'nhược điểm', 'biện luận', 'phản biện', 'tiêu chí đánh giá', 'hạn chế', 'lợi ích']):
        return 5 if clen >= 400 else 4
    if any(w in c for w in ['so sánh', 'nguyên nhân', 'mối quan hệ', 'ảnh hưởng', 'tác động', 'phân loại', 'phân biệt']):
        return 4
    if any(w in c for w in ['các bước', 'quy trình', 'thực hiện', 'tính toán', 'áp dụng', 'vận dụng']):
        return 3
    if any(w in c for w in ['giải thích', 'ý nghĩa', 'khái niệm', 'bao gồm', 'mô tả', 'trình bày']):
        return 2
    # Mặc định: nội dung dài → cho ceiling cao hơn để không bị chặn oan
    if clen >= 800:
        return 5
    if clen >= 400:
        return 4
    return 3  # mặc định: Bloom 3 (cho cơ hội thử)


def new_agent1_bloom_feasibility(section_content, section_title, target_bloom,
                                  request_id, user_id, document_id, plan_item_id,
                                  attempt=1, bloom_ceiling=None):
    """Agent 1: Kiểm tra section có đủ nội dung để sinh câu Bloom yêu cầu không.
    - Nếu quá ngắn hoặc bloom_ceiling < target → trả về feasible=False → bỏ qua section.
    Tham số:
      section_content : nội dung text của section đang xét
      section_title   : tiêu đề section (dùng để log)
      target_bloom    : cấp độ Bloom yêu cầu, VD 'Bloom 4 (Phân tích)'
      request_id      : ID yêu cầu xử lý (dùng cho DB log)
      plan_item_id    : ID câu hỏi trong kế hoạch, VD 'plan_1'
      attempt         : lần thử thứ mấy (hiện luôn = 1 với A1)
      bloom_ceiling   : cấp Bloom tối đa section hỗ trợ (pre-computed bởi _get_section_bloom_ceiling)
    Trả về: (feasible: bool, quality: float 0–1, reasons: list[str])
    """
    bloom_key = target_bloom.split('(')[0].strip()  # 'Bloom 4'
    try:
        bloom_num = int(bloom_key.replace('Bloom ', ''))  # 4
    except Exception:
        bloom_num = 2

    content_len = len(section_content.strip())  # độ dài ký tự của section
    word_count  = len(section_content.split())  # số từ của section

    # Ngưỡng ký tự/từ tối thiểu theo Bloom
    # Section ngắn (≤300 chars, VD đoạn test): hạ ngưỡng xuống để không reject oan
    # Section dài (giáo trình thật): giữ ngưỡng cao để đảm bảo chất lượng
    if content_len <= 300:
        min_len   = {1: 40,  2: 40,  3: 40,  4: 40,  5: 40,  6: 40}
        min_words = {1: 10,  2: 10,  3: 10,  4: 10,  5: 10,  6: 10}
    else:
        min_len   = {1: 150, 2: 200, 3: 300, 4: 400, 5: 400, 6: 400}  # ký tự tối thiểu
        min_words = {1: 30,  2: 50,  3: 80,  4: 100, 5: 100, 6: 100}  # từ tối thiểu

    reasons  = []    # lý do pass/fail — lưu vào DB
    quality  = 0.70  # điểm chất lượng mặc định
    feasible = True  # mặc định là đủ điều kiện

    # ── Kiểm tra 1: Độ dài tối thiểu ─────────────────────────────────────────
    if content_len < min_len.get(bloom_num, 200):
        # Section quá ngắn → không đủ nội dung để sinh câu hỏi
        feasible = False
        reasons.append(f'content_too_short({content_len}<{min_len.get(bloom_num,200)})')
        quality = 0.2
    elif word_count < min_words.get(bloom_num, 50):
        # Quá ít từ → không đủ nội dung
        feasible = False
        reasons.append(f'word_count_too_low({word_count})')
        quality = 0.3
    else:
        content_lower = section_content.lower()
        if bloom_num >= 4:
            # Bloom 4-6 cần từ khóa phân tích/đánh giá/đề xuất
            signals = ['so sánh', 'phân tích', 'đánh giá', 'mối quan hệ', 'nguyên nhân',
                       'kết quả', 'ảnh hưởng', 'tác động', 'thiết kế', 'đề xuất', 'cải tiến']
            found = sum(1 for s in signals if s in content_lower)  # đếm tín hiệu phân tích
            if found >= 2:
                quality = 0.85; reasons.append('rich_analytical_content')
            elif found >= 1:
                quality = 0.70; reasons.append('moderate_analytical_content')
            else:
                quality = 0.55; reasons.append('limited_analytical_signals')
        else:
            # Bloom 1-3 chỉ cần từ khóa khái niệm/quy trình cơ bản
            signals = ['là', 'bao gồm', 'gồm có', 'các bước', 'quy trình',
                       'phương pháp', 'nguyên tắc', 'định nghĩa']
            found = sum(1 for s in signals if s in content_lower)
            quality = min(0.90, 0.65 + found * 0.04)  # tăng dần theo số tín hiệu

    # ── Kiểm tra 2: Semantic Bloom ceiling (AI đã phân tích trước) ────────────
    # Nếu nội dung section chỉ hỗ trợ tối đa Bloom 2 mà yêu cầu Bloom 4 → fail ngay
    if feasible and bloom_ceiling is not None:
        effective_ceiling = _effective_bloom_ceiling(bloom_ceiling, bloom_num, content_len)
        if content_len <= 300 and bloom_num <= 3:
            # Đoạn ngắn B1–B3: phải khớp đúng cấp (strict)
            if bloom_ceiling != bloom_num:
                feasible = False
                reasons.append(f'short_exact_mismatch(exact={bloom_ceiling}!=target={bloom_num})')
                quality = min(quality, 0.25)
                print(f"    Agent 1: ❌ đoạn ngắn Bloom exact={bloom_ceiling} ≠ target={bloom_num} → bỏ qua")
            else:
                quality = min(1.0, quality + 0.05)
                reasons.append(f'short_exact_match(exact={bloom_ceiling}=target={bloom_num})')
        elif bloom_num > effective_ceiling:
            feasible = False
            reasons.append(f'semantic_ceiling({bloom_ceiling})<target({bloom_num})')
            quality = min(quality, 0.30)
            print(f"    Agent 1: ❌ ngữ nghĩa ceiling=Bloom {bloom_ceiling} (eff={effective_ceiling}) < yêu cầu=Bloom {bloom_num} → không phù hợp")
        elif bloom_num == effective_ceiling:
            quality = min(1.0, quality + 0.05)
            reasons.append(f'semantic_ceiling_match({bloom_ceiling},eff={effective_ceiling})')
        else:
            reasons.append(f'semantic_ceiling_above({bloom_ceiling}>={bloom_num},eff={effective_ceiling})')

    decision = 'pass' if feasible else 'fail'
    if user_id is not None:
        log = Agent1EvaluationLog(
            request_id=request_id, user_id=user_id, document_id=document_id,
            source_type='section', attempt=attempt,
            extraction_method='bloom_feasibility_check',
            decision=decision, terminal_status=decision,
            quality_score=round(quality, 4),
            reasons_json=json.dumps(reasons),
            metrics_json=json.dumps({
                'content_len': content_len, 'word_count': word_count,
                'bloom_num': bloom_num, 'bloom_ceiling': bloom_ceiling,
                'section_title': section_title,
            }),
        )
        db.session.add(log)
    ceiling_str = f", ceiling=B{bloom_ceiling}" if bloom_ceiling is not None else ""
    print(f"    Agent 1: {decision} — '{section_title[:50]}' ({content_len}c, bloom={bloom_num}{ceiling_str}, q={quality:.2f})")
    return feasible, round(quality, 4), reasons


def new_agent2_generate_qa(section_content, section_title, target_bloom, required_points,
                            request_id, user_id, document_id, plan_item_id, attempt=1,
                            chapter_context=None):
    """Agent 2: Gọi AI để sinh cặp câu hỏi + đáp án dựa hoàn toàn vào section.
    - Câu hỏi phải dùng đúng động từ Bloom, đáp án phải lấy từ tài liệu.
    Tham số:
      section_content  : nội dung text của section nguồn (MỤC cụ thể — nguồn chính)
      section_title    : tiêu đề section
      target_bloom     : cấp Bloom yêu cầu, VD 'Bloom 3 (Vận dụng)'
      required_points  : số ý cần có trong đáp án (tính từ điểm, VD 2đ → 8 ý)
      attempt          : lần thử thứ mấy (1–5); từ lần 2 AI được yêu cầu đổi góc độ
      chapter_context  : nội dung chương (bối cảnh mở rộng, không bắt buộc)
    Trả về: (question: str, answer: str, model_used: str) hoặc (None, None, None) nếu lỗi
    """
    bloom_key = target_bloom.split('(')[0].strip()  # 'Bloom 3'
    try:
        bloom_num = int(bloom_key.replace('Bloom ', ''))  # 3
    except Exception:
        bloom_num = 2

    # Động từ đặc trưng của từng cấp Bloom — đưa vào prompt để AI dùng đúng
    # Phát hiện ngôn ngữ tài liệu để chỉ thị AI trả lời đúng ngôn ngữ
    _doc_is_english = _is_english_content(section_content)

    if _doc_is_english:
        bloom_verbs = {
            1: "List / Name / Define / State / Identify",
            2: "Explain / Describe / Summarize / Clarify / Outline",
            3: "Apply / Use / Demonstrate / Implement / Calculate",
            4: "Analyze / Compare / Classify / Differentiate / Examine",
            5: "Evaluate / Assess / Argue / Justify / Critique",
            6: "Design / Create / Propose / Develop / Construct",
        }
        bloom_ans_guide = {
            1: "List concisely, quoting directly from the document.",
            2: "Explain each point clearly based on the document content.",
            3: "Each answer point = one action/step in the scenario, with concrete details from the document.",
            4: "Analyze each point: cause / effect / relationships.",
            5: "Provide an evaluative argument supported by the document.",
            6: (
                "Each point must be 1 specific solution/initiative. "
                "Format: '- [Action + object]: explanation based on the document'. "
                "Do NOT repeat headings like 'PROPOSAL:' for every point."
            ),
        }
        _lang_instruction = "\n🌐 LANGUAGE: The document is in ENGLISH. Write BOTH the question AND answer in ENGLISH only.\n"
    else:
        bloom_verbs = {
            1: "Liệt kê / Nêu / Kể tên / Định nghĩa / Cho biết",
            2: "Giải thích / Trình bày / Mô tả / Lý giải / Làm rõ",
            3: "Áp dụng / Vận dụng / Sử dụng / Thực hiện / Tính toán",
            4: "Phân tích / Phân loại / So sánh / Đối chiếu / Phân biệt",
            5: "Đánh giá / Nhận xét / Biện luận / Phản biện / Lập luận",
            6: "Đề xuất / Thiết kế / Sáng tạo / Xây dựng / Phát triển",
        }
        bloom_ans_guide = {
            1: "Liệt kê ngắn gọn, trích nguyên văn từ tài liệu.",
            2: "Giải thích rõ từng ý dựa trên nội dung tài liệu.",
            3: "Mỗi ý = một bước hành động/xử lý trong tình huống, kèm chi tiết cụ thể từ tài liệu (số liệu, thuật ngữ, quy trình).",
            4: "Phân tích từng điểm: nguyên nhân / hệ quả / mối quan hệ.",
            5: "Đưa ra luận điểm đánh giá có căn cứ từ tài liệu.",
            6: (
                "Mỗi ý phải là 1 giải pháp/sáng kiến cụ thể. "
                "Format: '- [Hành động + đối tượng]: giải thích cách thực hiện dựa trên tài liệu'. "
                "Ví dụ: '- Phát triển nền tảng thanh toán điện tử: ...', '- Xây dựng chiến lược tiếp thị số: ...'. "
                "KHÔNG viết tiêu đề kiểu 'ĐỀ XUẤT:', 'Đề xuất:' lặp lại mọi đầu ý."
            ),
        }
        _lang_instruction = "\n🌐 NGÔN NGỮ: Tài liệu tiếng Việt. Viết câu hỏi VÀ đáp án bằng TIẾNG VIỆT.\n"

    verbs    = bloom_verbs.get(bloom_num, "Trình bày" if not _doc_is_english else "Explain")
    ans_hint = bloom_ans_guide.get(bloom_num, "Trả lời dựa trên tài liệu." if not _doc_is_english else "Answer based on the document.")

    # Retry note: mỗi lần thử yêu cầu đổi góc nhìn câu hỏi khác hẳn
    if bloom_num == 3:
        if _doc_is_english:
            _retry_angles = [
                '',
                'Use a concrete scenario (business, learner, organization) that must solve a problem.',
                'Ask for STEPS to complete a task using knowledge from the section.',
                'Pose a practical problem and require applying a method from the document.',
                'Change the scenario context but keep the application requirement.',
            ]
        else:
            _retry_angles = [
                '',
                'Đặt TÌNH HUỐNG cụ thể (doanh nghiệp, người học, tổ chức) cần giải quyết vấn đề.',
                'Yêu cầu các BƯỚC THỰC HIỆN nhiệm vụ dựa trên quy trình trong tài liệu.',
                'Đưa bài toán thực tế và yêu cầu vận dụng phương pháp có trong mục nguồn.',
                'Đổi bối cảnh tình huống nhưng vẫn bám nội dung mục nguồn.',
            ]
    elif _doc_is_english:
        _retry_angles = [
            '',
            'Ask from the LEARNER perspective applying knowledge to a real situation.',
            'Focus the question on PROCESS or STEPS of implementation.',
            'Ask about COMPARISON or CHOICE between approaches.',
            'Ask about EVALUATING advantages/disadvantages or IMPACT.',
        ]
    else:
        _retry_angles = [
            '',
            'Đặt câu hỏi từ góc độ NGƯỜI HỌC áp dụng vào thực tế.',
            'Đặt câu hỏi tập trung vào QUY TRÌNH hoặc CÁC BƯỚC thực hiện.',
            'Đặt câu hỏi về SO SÁNH hoặc LỰA CHỌN giữa các phương án.',
            'Đặt câu hỏi về ĐÁNH GIÁ ưu/nhược điểm hoặc TÁC ĐỘNG.',
        ]
    retry_note = f"\n⚠️ [Lần thử {attempt}] {_retry_angles[min(attempt-1, len(_retry_angles)-1)]}" if attempt >= 2 else ""
    if attempt >= 3:
        retry_note += (
            "\n⚠️ Mỗi ý đáp án phải khác KHÍA CẠNH (mục đích / đối tượng / thời gian / hạn chế / hệ quả) — "
            "KHÔNG có 2 ý cùng chủ đề (VD: 'kết nối máy tính' và 'kết nối toàn cầu')."
            if not _doc_is_english else
            "\n⚠️ Each answer point must cover a DIFFERENT aspect (purpose / audience / time / limitation / outcome) — "
            "NO two points on the same theme (e.g. 'computer connectivity' and 'global connectivity')."
        )

    # Quy tắc chung cho ĐÁP ÁN — áp dụng mọi cấp Bloom
    _common_answer_rules = (
        "\n🚫 QUY TẮC CHUNG CHO ĐÁP ÁN (mọi cấp Bloom):\n"
        "- KHÔNG viết meta-comment như '(Không có ý thứ N trong tài liệu)', '(Tài liệu không đề cập)', '(Không đủ thông tin)' — đây là lỗi nghiêm trọng.\n"
        "- Tiêu đề ý KHÔNG được trùng với nội dung ý: '- Khái niệm: khái niệm' là SAI; phải là '- Khái niệm: [định nghĩa thực tế]'.\n"
        "- Nội dung mỗi ý phải là thông tin CỤ THỂ: số liệu, tên gọi, đặc điểm, quy trình — không phải câu mơ hồ.\n"
        "- Nếu tài liệu không đủ N ý riêng biệt: tách 1 ý thành 2 ý con chi tiết hơn, hoặc bổ sung số liệu/ví dụ cụ thể từ đoạn.\n"
        "- Mỗi ý phải nói về KHÍA CẠNH KHÁC NHAU (mục đích / đối tượng / thời gian / phương pháp / kết quả / hạn chế...) — KHÔNG lặp cùng một ý bằng từ khác.\n"
        "- SAI: ý 2 nói 'kết nối máy tính', ý 3 nói 'kết nối toàn cầu' (cùng chủ đề, chỉ khác phạm vi).\n"
        "- ĐÚNG: ý 1 = mục đích ban đầu, ý 2 = đối tượng sử dụng, ý 3 = hạn chế thời kỳ, ý 4 = hệ quả sau này.\n"
        "- Tiêu đề các ý KHÔNG được cùng chủ đề (VD: 'Khả năng cốt lõi' và 'Tiềm năng tương lai' đều nói về kết nối → SAI).\n"
    )

    # Bloom 5-6: cho phép paraphrase (diễn đạt lại) — không yêu cầu copy nguyên văn
    if bloom_num >= 5:
        grounding_rule = (
            "Đáp án phải hoàn toàn dựa trên khái niệm, ý tưởng và thuật ngữ TRONG tài liệu.\n"
            "Ưu tiên dùng CHÍNH XÁC các thuật ngữ, cụm từ kỹ thuật xuất hiện trong đoạn MỤC NGUỒN.\n"
            "Có thể diễn đạt lại bằng từ ngữ khác nhưng TUYỆT ĐỐI không:\n"
            "  - Dùng cấu trúc câu trả lời chung chung hoặc khuôn mẫu cố định\n"
            "  - Đề cập tên thương hiệu, công ty, sản phẩm nào KHÔNG có trong tài liệu\n"
            "  - Thêm URL, link, dẫn chứng từ nguồn ngoài tài liệu\n"
            "  - Bịa ra số liệu, ví dụ hoặc tình huống không có trong tài liệu"
            + _common_answer_rules
        )
    else:
        grounding_rule = (
            "Câu trả lời PHẢI sử dụng chính xác các từ, cụm từ và thuật ngữ xuất hiện trong đoạn MỤC NGUỒN.\n"
            "TUYỆT ĐỐI không dùng cấu trúc câu trả lời chung chung hoặc khuôn mẫu cố định.\n"
            "TUYỆT ĐỐI không thêm kiến thức bên ngoài tài liệu."
            + _common_answer_rules
        )

    # Bloom 3: siết bám MỤC NGUỒN — tình huống chỉ là khung, nội dung phải từ mục
    if bloom_num == 3:
        if _doc_is_english:
            grounding_rule = (
                "BLOOM 3 — STRICT SOURCE GROUNDING:\n"
                "- Question and answer MUST use ONLY concepts, terms, and facts from the SOURCE SECTION.\n"
                "- The scenario is just a framing device; answer content MUST come from the SOURCE SECTION.\n"
                "- Each answer point MUST include at least one term or phrase from the SOURCE SECTION.\n"
                "- Do NOT use information from chapter context if it is not in the SOURCE SECTION.\n"
                "- Do NOT invent numbers, names, or examples not in the section."
                + _common_answer_rules
            )
        else:
            grounding_rule = (
                "BLOOM 3 — BÁM NGUỒN NGHIÊM NGẶT:\n"
                "- Câu hỏi và đáp án CHỈ được dùng khái niệm, thuật ngữ, số liệu có trong đoạn MỤC NGUỒN.\n"
                "- Tình huống (Giả sử...) chỉ là khung diễn đạt; NỘI DUNG trả lời phải trích từ MỤC NGUỒN.\n"
                "- Mỗi ý đáp án PHẢI chứa ít nhất 1 thuật ngữ hoặc cụm từ xuất hiện trong MỤC NGUỒN.\n"
                "- TUYỆT ĐỐI KHÔNG lấy thông tin từ phần khác của chương nếu không có trong MỤC NGUỒN.\n"
                "- TUYỆT ĐỐI KHÔNG bịa số liệu, tên riêng, ví dụ không có trong mục."
                + _common_answer_rules
            )

    # Bloom 6: cảnh báo rõ không được liệt kê lại
    bloom6_extra = (
        "\n⚠️ Bloom 6 — Yêu cầu ĐẶC BIỆT:\n"
        "- Mỗi ý là 1 giải pháp hành động. Tiêu đề ngắn phải là cụm động từ hành động (ví dụ: 'Phát triển hệ thống...', 'Xây dựng chiến lược...', 'Triển khai mô hình...')\n"
        "- KHÔNG viết tiêu đề kiểu 'ĐỀ XUẤT:' hay 'Đề xuất:' lặp lại — điều đó trông rất xấu\n"
        "- KHÔNG liệt kê lại khái niệm, định nghĩa, tên gọi — đó là Bloom 1-2\n"
        "- Mỗi giải pháp phải dựa trên thuật ngữ/khái niệm có trong tài liệu"
    ) if bloom_num == 6 else ""

    # B1–B3: thêm ràng buộc chống "lạc cấp" lên B4
    bloom_low_constraint = ""
    if _doc_is_english:
        if bloom_num == 1:
            bloom_low_constraint = (
                "\n⚠️ BLOOM 1 (REMEMBER) — LOWEST LEVEL:\n"
                "Question MUST be short, only requiring recall / listing / defining.\n"
                "DO NOT use: 'aspects', 'evaluate', 'analyze', 'compare', 'why'\n"
                "Correct structures:\n"
                "  • 'Define [concept X].'\n"
                "  • 'List the [components / features] of [X].'\n"
                "  • 'Name the [types / steps] in [X].'\n"
                "WRONG: 'Identify the key aspects to consider when...' — that is B4!\n"
            )
        elif bloom_num == 2:
            bloom_low_constraint = (
                "\n⚠️ BLOOM 2 (UNDERSTAND) — SIMPLE EXPLANATION LEVEL:\n"
                "Question requires restating or explaining a specific concept.\n"
                "DO NOT use: 'evaluate', 'analyze', 'compare', 'why does X require'\n"
                "Correct structures:\n"
                "  • 'Explain what [concept X] is and how it works.'\n"
                "  • 'Describe the role / significance of [X] in [Y].'\n"
                "  • 'Outline the [process / mechanism] of [X].'\n"
                "  • 'Clarify the difference between [X] and [Y].'\n"
                "WRONG: 'Explain why applying X requires understanding of...' — that is B4!\n"
            )
        elif bloom_num == 3:
            bloom_low_constraint = (
                "\n⚠️ BLOOM 3 (APPLY) — PRACTICAL APPLICATION LEVEL:\n"
                "Question MUST set a CONCRETE scenario and ask to USE knowledge to solve a task.\n"
                "DO NOT use in the question: 'describe', 'explain', 'outline', 'list', 'state' — those are B1/B2!\n"
                "Correct structures:\n"
                "  • 'Suppose [scenario Z]. Apply [method X] to accomplish [task Y].'\n"
                "  • 'Using [X] from the document, demonstrate how to [specific task] in [context Z].'\n"
                "WRONG: 'Apply knowledge of X to describe how it works' — 'describe' is B2!\n"
                "\n🔴 ANSWER RULES FOR BLOOM 3:\n"
                "- Each point = one action/step in the scenario, NOT a definition.\n"
                "- WRONG: '- Online shopping: includes activities such as online shopping'\n"
                "- RIGHT: '- Payment setup: use electronic payment as described in the 1990s e-commerce context'\n"
            )
    else:
        if bloom_num == 1:
            bloom_low_constraint = (
                "\n⚠️ BLOOM 1 (NHỚ) — ĐÂY LÀ CẤP ĐỘ THẤP NHẤT:\n"
                "Câu hỏi PHẢI ngắn gọn, chỉ yêu cầu nhớ lại / liệt kê / định nghĩa.\n"
                "TUYỆT ĐỐI KHÔNG dùng: 'khía cạnh', 'xem xét', 'đánh giá', 'phân tích', 'so sánh', 'tại sao'\n"
                "Cấu trúc đúng (chọn 1):\n"
                "  • 'Định nghĩa [khái niệm X] là gì?'\n"
                "  • 'Liệt kê các [thành phần / đặc điểm] của [X].'\n"
                "  • 'Nêu [tên / khái niệm] liên quan đến [chủ đề].'\n"
                "  • 'Kể tên các [loại / bước] trong [X].'\n"
                "Cấu trúc SAI: 'Cho biết các khía cạnh cần xem xét khi [làm gì đó]' — đây là B4!\n"
                "\n🔴 LỖI THƯỜNG GẶP Ở BLOOM 1 — TUYỆT ĐỐI TRÁNH:\n"
                "1. Tiêu đề lặp nội dung: '- Khái niệm: khái niệm' → SAI! Phải là '- Khái niệm: [định nghĩa cụ thể từ tài liệu]'\n"
                "2. Nội dung mơ hồ: '- Việt Nam không phải là ngoại lệ' → SAI! Phải trích dữ kiện cụ thể.\n"
                "3. Meta-comment khi thiếu ý: '- (Không có kênh thứ tư...)' → TUYỆT ĐỐI KHÔNG! Nếu tài liệu chỉ có 3 điểm, hãy mở rộng 1 ý thành 2 ý con cụ thể hơn, hoặc trích thêm chi tiết số liệu/dẫn chứng từ đoạn.\n"
                "Mỗi ý đáp án PHẢI có: tiêu đề ngắn (1-3 từ) + dấu hai chấm + thông tin thực tế cụ thể từ tài liệu.\n"
            )
        elif bloom_num == 2:
            bloom_low_constraint = (
                "\n⚠️ BLOOM 2 (HIỂU) — CẤP ĐỘ GIẢI THÍCH ĐƠN GIẢN:\n"
                "Câu hỏi yêu cầu diễn đạt lại / giải thích một khái niệm cụ thể.\n"
                "TUYỆT ĐỐI KHÔNG dùng: 'khía cạnh', 'đánh giá', 'phân tích', 'so sánh', 'tại sao... đòi hỏi'\n"
                "Cấu trúc đúng (chọn 1):\n"
                "  • 'Giải thích [khái niệm X] là gì và hoạt động như thế nào.'\n"
                "  • 'Trình bày ý nghĩa / vai trò của [X] trong [Y].'\n"
                "  • 'Mô tả [quy trình / cơ chế] của [X].'\n"
                "  • 'Làm rõ sự khác nhau giữa [X] và [Y].'\n"
                "Cấu trúc SAI: 'Giải thích tại sao việc áp dụng X đòi hỏi sự hiểu biết về...' — đây là B4!\n"
            )
        elif bloom_num == 3:
            bloom_low_constraint = (
                "\n⚠️ BLOOM 3 (VẬN DỤNG) — PHẢI CÓ TÌNH HUỐNG + HÀNH ĐỘNG:\n"
                "Bloom 3 = dùng kiến thức trong tài liệu để GIẢI QUYẾT một nhiệm vụ/tình huống cụ thể.\n"
                "Câu hỏi BẮT BUỘC có tình huống: 'Giả sử...', 'Trong tình huống...', 'Nếu một doanh nghiệp...', 'Khi [đối tượng] cần...'\n"
                "TUYỆT ĐỐI KHÔNG dùng trong câu hỏi: 'mô tả', 'trình bày', 'giải thích', 'nêu', 'liệt kê', 'cho biết' — đó là B1/B2!\n"
                "TUYỆT ĐỐI KHÔNG dùng: 'phân tích', 'đánh giá', 'so sánh' — đó là B4/B5!\n"
                "Cấu trúc ĐÚNG:\n"
                "  • 'Giả sử [tình huống Z], hãy vận dụng [phương pháp X] để [thực hiện nhiệm vụ Y].'\n"
                "  • 'Sử dụng kiến thức về [X] trong tài liệu, hãy thực hiện các bước [Y] cho [đối tượng/bối cảnh Z].'\n"
                "Cấu trúc SAI (đây là B2, không phải B3):\n"
                "  • 'Vận dụng kiến thức về X, hãy mô tả/trình bày cách hoạt động...'\n"
                "  • 'Vận dụng kiến thức về X, hãy giải thích...'\n"
                "\n🔴 ĐÁP ÁN BLOOM 3 — TUYỆT ĐỐI TRÁNH:\n"
                "- Mỗi ý phải là BƯỚC HÀNH ĐỘNG trong tình huống, KHÔNG phải định nghĩa/lặp tên khái niệm.\n"
                "- SAI: '- Mua sắm trực tuyến: bao gồm các hoạt động như mua sắm trực tuyến'\n"
                "- SAI: '- Thanh toán điện tử: bao gồm các hoạt động như thanh toán điện tử'\n"
                "- ĐÚNG: '- Thu hút người mua: tập trung vào người dùng hơn thị trường mục tiêu vì họ quyết định thành công TMĐT'\n"
                "- ĐÚNG: '- Triển khai thanh toán: áp dụng hình thức thanh toán điện tử để hoàn tất giao dịch trực tuyến'\n"
                "\n📌 BÁM MỤC NGUỒN:\n"
                "- Tình huống chỉ dùng để đặt câu hỏi; mọi ý trong đáp án phải lấy chi tiết từ MỤC NGUỒN (không từ chương khác).\n"
                "- Mỗi ý phải có ít nhất 1 thuật ngữ/cụm từ trích từ MỤC NGUỒN.\n"
            )

    # Tự động phát hiện tài liệu STEM (toán, hóa, vật lý) để thêm hướng dẫn công thức
    _stem_signals = [
        # Ký hiệu toán học
        '∞', '∑', '∫', '∂', '∇', '±', '≤', '≥', '≠', '≈', '√',
        # Chữ Hy Lạp (toán/vật lý)
        'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'λ', 'μ', 'π', 'σ', 'τ', 'ω',
        'Α', 'Β', 'Γ', 'Δ', 'Σ', 'Ω',
        # Hóa học
        'H₂', 'O₂', 'CO₂', 'H₂O', 'Fe', 'Na', 'Cl', 'SO₄', 'NO₃', 'NH₃',
        # Vật lý
        'Δ', 'Ω', '°C', '°K', 'eV', 'mol', 'pH',
        # Dấu hiệu phương trình
        '→', '⇌', '↔', '⇒',
    ]
    _content_lower = section_content[:3000]
    _is_stem_content = (
        sum(1 for sig in _stem_signals if sig in _content_lower) >= 3
        or bool(re.search(r'[A-Z][a-z]?\d+[A-Z]?', section_content[:2000]))  # H2O, CO2, Fe2O3
        or bool(re.search(r'\^\{|\\frac|\\sum|\\int|\\sqrt', section_content[:2000]))  # LaTeX
    )

    stem_formula_guide = (
        "\n🔬 NỘI DUNG STEM (toán/hóa/vật lý): Hướng dẫn viết công thức dưới dạng văn bản thuần:\n"
        "- Phương trình hóa học: viết rõ chất, mũi tên '->', dấu '+'. Ví dụ: H2 + O2 -> H2O\n"
        "- Chỉ số dưới: dùng số liền (H2O, CO2, H2SO4) thay vì ký tự ừ (H₂O)\n"
        "- Lũy thừa: dùng dấu mũ (x^2, e^x, 10^-3)\n"
        "- Phân số: dùng dấu gạch (a/b, (x+1)/(x-1))\n"
        "- Căn bậc 2: sqrt(x), căn bậc n: x^(1/n)\n"
        "- Tích phân: tich_phan f(x) dx từ a đến b\n"
        "- Chuyển sang mô tả bằng lời nếu công thức quá phức tạp\n"
    ) if _is_stem_content else ""

    # Phần bối cảnh chương — Bloom 3 KHÔNG đưa (tránh trả lời lệch mục nguồn)
    chapter_ctx_block = ""
    if chapter_context and bloom_num != 3:
        # Lấy 2000 ký tự đầu chương làm bối cảnh (đủ để model hiểu ngữ cảnh tổng quan)
        ctx_preview = chapter_context[:2000].strip()
        chapter_ctx_block = (
            f"\n📖 BỐI CẢNH CHƯƠNG (chỉ để hiểu ngữ cảnh, KHÔNG dùng thay thế cho MỤC NGUỒN):\n"
            f"--- BẮT ĐẦU BỐI CẢNH ---\n{ctx_preview}\n--- KẾT THÚC BỐI CẢNH ---\n"
        )
    elif bloom_num == 3:
        chapter_ctx_block = (
            "\n⚠️ BLOOM 3: CHỈ được dùng đoạn MỤC NGUỒN phía trên. "
            "Không lấy thông tin từ phần khác của chương/tài liệu.\n"
        )

    prompt = (
        f"Bạn là giảng viên đại học. Tạo 1 cặp câu hỏi–đáp án DỰA HOÀN TOÀN vào đoạn MỤC NGUỒN dưới đây.\n"
        f"{_lang_instruction}"
        f"{grounding_rule}"
        f"{bloom6_extra}"
        f"{bloom_low_constraint}\n"
        f"{stem_formula_guide}\n"
        f"⭐ MỤC NGUỒN CHÍNH (bắt buộc lấy từ ngữ, thuật ngữ, nội dung từ đây — mục '{section_title}'):\n"
        f"--- BẮT ĐẦU MỤC ---\n{section_content[:3000]}\n--- KẾT THÚC MỤC ---\n"
        f"{chapter_ctx_block}\n"
        f"🎯 CẤP ĐỘ BLOOM: {target_bloom}\n"
        f"   Động từ bắt buộc: {verbs}\n"
        f"{retry_note}\n\n"
        f"📋 YÊU CẦU QUAN TRỌNG:\n"
        f"1. Câu hỏi: bắt đầu bằng một trong các động từ trên, 15–50 từ\n"
        f"2. Câu hỏi chỉ được chứa MỘT yêu cầu duy nhất — KHÔNG dùng 'và', 'cùng với' để ghép nhiều yêu cầu\n"
        f"   ⚠️ KHÔNG đặt số cụ thể trong câu hỏi (ví dụ: 'hai', 'ba', 'bốn', '2', '3', '4')\n"
        f"   Sai: 'Cho biết ba tên gọi...' | Đúng: 'Cho biết các tên gọi phổ biến...' hoặc 'Liệt kê những tên gọi...'\n"
        f"3. Đáp án: ĐÚNG {required_points} ý, mỗi ý bắt đầu bằng '- tiêu đề ngắn: nội dung'\n"
        f"   ⚠️ Mỗi ý phải khác KHÍA CẠNH — không có 2 ý cùng nói một chủ đề (VD: 2 ý đều về 'kết nối')\n"
        f"4. {ans_hint}\n"
        f"5. Mỗi ý PHẢI sử dụng từ ngữ, cụm từ cụ thể lấy trực tiếp từ MỤC NGUỒN trên\n"
        f"6. KHÔNG thêm bất kỳ thông tin nào không có trong tài liệu\n"
        f"7. KHÔNG dùng **, [], KHÔNG đánh số ý\n\n"
        f"Format bắt buộc:\n"
        f"BLOOM: {bloom_key}\n"
        f"QUESTION: [câu hỏi]\n"
        f"ANSWER:\n[đáp án {required_points} ý, mỗi ý một dòng bắt đầu bằng '- ']"
    )

    reasons = []
    try:
        response = ai_client.chat.completions.create(
            model=_cfg.QUESTION_MODEL,
            messages=[
                {"role": "system", "content":
                 ("Respond ONLY in this exact format, no extra text:\n"
                  "BLOOM: [level]\n"
                  "QUESTION: [question text]\n"
                  "ANSWER:\n- [point]: [content]\n"
                  "Do not add preamble or text outside this format.\n"
                  + ("Write question and answer in ENGLISH only." if _doc_is_english
                     else "Viết câu hỏi và đáp án bằng TIẾNG VIỆT."))},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1500,
            timeout=60,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown bold ma GPT them vao (VD: **BLOOM:** **QUESTION:**)
        raw = re.sub(r'\*\*([A-Z]+:?)\*\*', r'\1', raw)  # **BLOOM:** -> BLOOM:
        raw = re.sub(r'\*\*', '', raw)                       # con lai ** -> bo

        # Parse ket qua tra ve cua AI theo format da yeu cau
        bloom_m    = re.search(r'BLOOM:\s*(.+?)(?:\n|$)', raw, re.IGNORECASE)
        question_m = re.search(r'QUESTION:\s*(.+?)(?:\nANSWER:|$)', raw, re.DOTALL | re.IGNORECASE)
        answer_m   = re.search(r'ANSWER:\s*\n(.+)', raw, re.DOTALL | re.IGNORECASE)
        if not answer_m:  # some models put answer on same line as ANSWER:
            answer_m = re.search(r'ANSWER:\s*(-\s*.+)', raw, re.DOTALL | re.IGNORECASE)

        question = question_m.group(1).strip() if question_m else None  # câu hỏi
        answer   = answer_m.group(1).strip()   if answer_m   else None  # đáp án

        if not question or not answer:
            raise ValueError(f"Could not parse Q/A. Raw: {raw[:300]}")

        answer = _enforce_point_count(answer, required_points)  # cắt/giữ đúng số ý
        answer = clean_answer_formatting(answer)                 # làm sạch format

        reasons.append('generation_success')
        decision = 'pass'
        quality  = 0.75  # điểm mặc định khi sinh thành công (A3 sẽ đánh giá thực sự)

    except Exception as e:
        print(f"     ❌ Agent 2 lỗi: {e}")
        question = answer = None
        reasons.append('generation_failed')
        decision = 'fail'
        quality  = 0.0

    if user_id is not None:
        log = Agent2EvaluationLog(
            request_id=request_id, user_id=user_id, document_id=document_id,
            attempt=attempt, decision=decision, terminal_status=decision,
            quality_score=round(quality, 4),
            reasons_json=json.dumps(reasons),
            structure_summary_json=json.dumps({'section_title': section_title, 'bloom': target_bloom}),
            plan_summary_json=json.dumps({'plan_item_id': plan_item_id, 'required_points': required_points}),
        )
        db.session.add(log)

    return question, answer, (_cfg.QUESTION_MODEL if decision == 'pass' else None)


def _a3_bloom3_question_score(question: str) -> float:
    """Đánh giá câu hỏi Bloom 3 có thật sự 'vận dụng trong tình huống' hay chỉ mô tả (B2)."""
    q = question.lower()
    b2_drift = ['mô tả', 'trình bày', 'giải thích', 'nêu ', 'liệt kê', 'cho biết', 'làm rõ', 'tóm tắt']
    if any(v in q for v in b2_drift):
        return 0.25
    scenario = ['giả sử', 'tình huống', 'trong trường hợp', 'nếu ', 'khi một', 'khi doanh nghiệp',
                'khi người', 'khi công ty', 'khi cửa hàng', 'trong bối cảnh', 'để thực hiện',
                'cần triển khai', 'cần áp dụng', 'muốn bán', 'muốn triển khai']
    has_scenario = any(m in q for m in scenario)
    b3_verbs = ['áp dụng', 'vận dụng', 'sử dụng', 'thực hiện', 'triển khai', 'tính toán']
    has_b3 = any(v in q for v in b3_verbs)
    if has_b3 and has_scenario:
        return 1.0
    if has_b3:
        return 0.45
    return 0.35


def _a3_tautology_score(answer: str) -> float:
    """Phát hiện đáp án lặp tiêu đề (VD: 'Khái niệm: khái niệm'). Trả về 0–1, cao = tốt."""
    lines = [ln.strip() for ln in answer.splitlines() if ln.strip().startswith('-')]
    if not lines:
        return 1.0
    bad = 0
    for line in lines:
        m = re.match(r'-\s*([^:]+):\s*(.+)', line, re.IGNORECASE)
        if not m:
            continue
        title = re.sub(r'\s+', ' ', m.group(1).strip().lower())
        content = re.sub(r'\s+', ' ', m.group(2).strip().lower())
        if not title or not content:
            continue
        if title == content:
            bad += 1
            continue
        if content.startswith('bao gồm các hoạt động như') and title in content:
            bad += 1
            continue
        if len(content) <= len(title) + 5 and title in content:
            bad += 1
    return max(0.2, 1.0 - (bad / len(lines)) * 0.85)


# Cụm từ chung, không đủ để kết luận trùng ý
_A3_GENERIC_PHRASES = frozenset({
    'trong thời gian', 'theo tài liệu', 'điều này', 'điều đó', 'của internet',
    'của mạng', 'trong giai đoạn', 'sự phát triển', 'đã tạo', 'điều kiện cho',
    'một mạng', 'các mục', 'các mục đích', 'in the', 'of the', 'this is',
    'that is', 'as a', 'for the',
})

# Từ yếu trong tiêu đề — trùng nhau không đủ kết luận trùng ý
_A3_WEAK_TITLE_WORDS = frozenset({
    'khả', 'năng', 'tiềm', 'tương', 'lai', 'cốt', 'lõi', 'giai', 'đoạn',
    'mục', 'đích', 'vai', 'trò', 'ý', 'nghĩa', 'thời', 'điểm', 'ban', 'đầu',
    'core', 'future', 'potential', 'capability', 'initial', 'stage', 'aspect',
})

# Từ chung trong nội dung — loại khi tính Jaccard để tránh false negative
_A3_WEAK_CONTENT_WORDS = frozenset({
    'internet', 'mạng', 'lưới', 'hệ', 'thống', 'thương', 'mại', 'điện', 'tử',
    'phát', 'triển', 'tạo', 'điều', 'kiện', 'trong', 'các', 'cho', 'được',
    'network', 'system', 'development', 'global', 'computer', 'computers',
})


def _a3_parse_answer_points(answer: str) -> list[tuple[str, str]]:
    """Tách các ý dạng '- tiêu đề: nội dung' thành (title, content)."""
    points: list[tuple[str, str]] = []
    for line in answer.splitlines():
        line = line.strip()
        if not line.startswith('-'):
            continue
        m = re.match(r'-\s*([^:]+):\s*(.+)', line, re.IGNORECASE)
        if m:
            points.append((m.group(1).strip(), m.group(2).strip()))
        else:
            points.append(('', line.lstrip('- ').strip()))
    return points


def _a3_pairwise_point_overlap(title_a: str, content_a: str, title_b: str, content_b: str) -> float:
    """Mức trùng lặp giữa 2 ý (0–1, cao = gần nghĩa / trùng chủ đề)."""
    text_a = re.sub(r'\s+', ' ', f"{title_a} {content_a}".lower()).strip()
    text_b = re.sub(r'\s+', ' ', f"{title_b} {content_b}".lower()).strip()
    if not text_a or not text_b:
        return 0.0

    phrase_score = 0.0
    words_a = text_a.split()
    for length in range(min(5, len(words_a)), 1, -1):
        found = False
        for i in range(len(words_a) - length + 1):
            phrase = ' '.join(words_a[i:i + length])
            if len(phrase) < 8 or phrase in _A3_GENERIC_PHRASES:
                continue
            if phrase in text_b:
                sig = [w for w in phrase.split() if len(w) >= 4 and w not in _STOP_VI]
                if sig:
                    phrase_score = max(phrase_score, min(1.0, len(phrase) / 28))
                    found = True
                    break
        if found:
            break

    tok_a = set(re.findall(r'\w{3,}', content_a.lower())) - _STOP_VI - _A3_WEAK_CONTENT_WORDS
    tok_b = set(re.findall(r'\w{3,}', content_b.lower())) - _STOP_VI - _A3_WEAK_CONTENT_WORDS
    jaccard = (len(tok_a & tok_b) / len(tok_a | tok_b)) if tok_a and tok_b else 0.0

    title_a_t = set(re.findall(r'\w{3,}', title_a.lower())) - _A3_WEAK_TITLE_WORDS
    title_b_t = set(re.findall(r'\w{3,}', title_b.lower())) - _A3_WEAK_TITLE_WORDS
    title_j = (len(title_a_t & title_b_t) / len(title_a_t | title_b_t)) if title_a_t and title_b_t else 0.0

    strong_shared = {w for w in (tok_a & tok_b) if len(w) >= 5}
    theme_score = min(0.55, len(strong_shared) * 0.22) if strong_shared else 0.0

    overlap = phrase_score
    if jaccard >= 0.30:
        overlap = max(overlap, jaccard * 0.90)
    if title_j >= 0.50:
        overlap = max(overlap, title_j * 0.45)
    if theme_score >= 0.22:
        overlap = max(overlap, theme_score)
    return round(min(overlap, 1.0), 4)


def _a3_answer_diversity_score(answer: str) -> tuple[float, float]:
    """Đánh giá đa dạng giữa các ý trong đáp án.
    Trả về (diversity_score 0–1 cao=tốt, max_pair_overlap 0–1 cao=trùng ý).
    """
    points = _a3_parse_answer_points(answer)
    if len(points) < 2:
        return 1.0, 0.0

    max_overlap = 0.0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            ov = _a3_pairwise_point_overlap(points[i][0], points[i][1], points[j][0], points[j][1])
            max_overlap = max(max_overlap, ov)

    if max_overlap >= 0.50:
        diversity = 0.15
    elif max_overlap >= 0.38:
        diversity = max(0.25, 0.88 - max_overlap)
    elif max_overlap >= 0.25:
        diversity = max(0.45, 0.95 - max_overlap * 0.75)
    else:
        diversity = max(0.72, 1.0 - max_overlap * 0.45)
    return round(diversity, 4), round(max_overlap, 4)


def new_agent3_evaluate_qa(question, answer, section_content, section_title, target_bloom,
                            request_id, user_id, document_id, plan_item_id, attempt=1):
    """Agent 3: Đánh giá chất lượng cặp Q&A do Agent 2 sinh ra.
    Nếu pass → pipeline lưu kết quả. Nếu fail → Agent 2 thử lại (tối đa 5 lần).
    Tham số:
      question        : câu hỏi do Agent 2 sinh
      answer          : đáp án do Agent 2 sinh
      section_content : nội dung gốc của section (dùng để so sánh)
      attempt         : lần thử thứ mấy của vòng lặp A2→A3
    Trả về: (decision: 'pass'|'fail', quality: float 0–1)
    """
    bloom_key = target_bloom.split('(')[0].strip()  # 'Bloom 4'
    try:
        bloom_num = int(bloom_key.replace('Bloom ', ''))  # 4
    except Exception:
        bloom_num = 2

    # ── Tính chỉ số đánh giá ────────────────────────────────────────────────
    # q_faithfulness: tỉ lệ từ của câu hỏi có trong section (0–1)
    q_faithfulness = _a3_word_overlap(question, section_content)

    # Bloom 4: phân tích thường paraphrase → kết hợp ngram + concept
    # Bloom 5-6: dùng concept overlap (khái niệm/thuật ngữ) thay vì n-gram verbatim
    if bloom_num >= 5:
        a_groundedness = _a3_concept_overlap(answer, section_content)
        ground_method  = 'concept'
    elif bloom_num == 4:
        ngram_score = _a3_ngram_groundedness(answer, section_content)
        concept_score = _a3_concept_overlap(answer, section_content)
        a_groundedness = round(max(ngram_score, concept_score * 0.92), 4)
        ground_method  = 'hybrid'
    else:
        a_groundedness = _a3_ngram_groundedness(answer, section_content)
        ground_method  = 'ngram'

    # Kiểm tra câu hỏi có bắt đầu bằng động từ đúng Bloom không
    _bloom_verbs = {
        1: ['liệt kê', 'nêu', 'kể tên', 'định nghĩa', 'cho biết', 'trình bày'],
        2: ['giải thích', 'mô tả', 'lý giải', 'làm rõ', 'diễn giải', 'tóm tắt'],
        3: ['áp dụng', 'vận dụng', 'sử dụng', 'thực hiện', 'tính toán', 'triển khai'],
        4: ['phân tích', 'phân loại', 'so sánh', 'đối chiếu', 'phân biệt', 'tìm nguyên nhân'],
        5: ['đánh giá', 'nhận xét', 'biện luận', 'phản biện', 'lập luận', 'bình luận'],
        6: ['đề xuất', 'thiết kế', 'sáng tạo', 'xây dựng', 'phát triển', 'cải tiến'],
    }
    q_lower = question.lower()
    has_bloom_verb   = any(v in q_lower for v in _bloom_verbs.get(bloom_num, []))
    bloom_verb_score = 0.90 if has_bloom_verb else 0.35  # có động từ đúng → 0.90, không → 0.35

    reasons = []  # lý do để lưu vào DB log
    if q_faithfulness >= 0.40:   reasons.append('question_grounded')
    elif q_faithfulness >= 0.25: reasons.append('question_partially_grounded')
    else:                         reasons.append('question_low_overlap')

    if a_groundedness >= 0.40:   reasons.append(f'answer_grounded({ground_method})')
    elif a_groundedness >= 0.25: reasons.append(f'answer_partially_grounded({ground_method})')
    else:                         reasons.append(f'answer_low_overlap({ground_method})')

    if has_bloom_verb: reasons.append('bloom_verb_correct')
    else:              reasons.append('bloom_verb_missing')

    # Bloom 3: kiểm tra câu hỏi có tình huống thật + đáp án không lặp tiêu đề
    bloom3_q_score = 1.0
    tautology_score = 1.0
    diversity_score, max_point_overlap = _a3_answer_diversity_score(answer)
    if diversity_score < 0.55:
        reasons.append('answer_points_overlap')
    if bloom_num == 3:
        bloom3_q_score = _a3_bloom3_question_score(question)
        tautology_score = _a3_tautology_score(answer)
        key_term_score = _a3_concept_overlap(answer, section_content)
        if bloom3_q_score < 0.40:
            reasons.append('bloom3_not_scenario')
        if tautology_score < 0.55:
            reasons.append('answer_tautological')
        if key_term_score < 0.40:
            reasons.append('bloom3_low_key_terms')
        if q_faithfulness < 0.35:
            reasons.append('bloom3_question_off_source')
    else:
        key_term_score = 1.0

    # Bloom 6: kiểm tra đáp án có động từ sáng tạo không (không chỉ liệt kê)
    answer_creative_score = 1.0
    if bloom_num == 6:
        _creative_verbs = ['đề xuất', 'thiết kế', 'xây dựng', 'phát triển', 'tạo ra',
                           'cải tiến', 'đề nghị', 'kiến nghị', 'sáng tạo']
        has_creative = any(v in answer.lower() for v in _creative_verbs)
        if not has_creative:
            answer_creative_score = 0.25
            reasons.append('answer_not_creative_bloom6')
            print(f"    Agent 3: ⚠️ Bloom 6 — đáp án thiếu động từ sáng tạo → creative_score=0.25")
        else:
            reasons.append('answer_creative_bloom6')

    # ── Hard floor ─────────────────────────────────────────────────────────────
    # Bloom 5-6 dùng concept_overlap floor thấp hơn vì đáp án paraphrase hợp lệ
    # Đoạn ngắn (≤300 chars): vocab rất hạn chế → câu B6 đề xuất cái mới không thể
    #   share nhiều từ với passage → hạ floor xuống 0.05 để không HARD FAIL oan
    src_len = len(section_content.strip())
    if bloom_num >= 5 and src_len <= 300:
        hard_floor = 0.05   # passage quá ngắn, không thể expect cao hơn
    elif bloom_num >= 5:
        hard_floor = 0.15   # B5-6: paraphrase/đánh giá hợp lệ
    elif bloom_num == 4:
        hard_floor = 0.28   # B4: phân tích, cho phép diễn đạt lại
    elif bloom_num == 3:
        hard_floor = 0.52   # Bloom 3: đáp án phải bám chặt mục nguồn
    else:
        hard_floor = 0.35   # Bloom 1-2: đáp án factual phải bám sát tài liệu
    if a_groundedness < hard_floor:
        quality  = round(a_groundedness, 4)
        decision = 'fail'
        print(f"    Agent 3: HARD FAIL — đáp án không bám tài liệu ({ground_method}={a_groundedness:.3f} < {hard_floor})")
        if user_id is not None:
            log = Agent3EvaluationLog(
                request_id=request_id, user_id=user_id, document_id=document_id,
                plan_item_id=plan_item_id, attempt=attempt,
                decision=decision, terminal_status=decision,
                quality_score=quality, reasons_json=json.dumps(reasons),
                target_bloom=bloom_key, generated_bloom=bloom_key,
                validated_bloom=bloom_key, bloom_match_type='strict_match',
                source_faithfulness_score=round(q_faithfulness, 4),
                scoreability_score=round(bloom_verb_score, 4),
            )
            db.session.add(log)
        return decision, quality

    # Bloom 3 hard fail: lạc B2, lặp tiêu đề, hoặc không bám mục nguồn
    if bloom_num == 3 and (
        bloom3_q_score < 0.30
        or tautology_score < 0.40
        or a_groundedness < 0.50
        or key_term_score < 0.35
        or q_faithfulness < 0.30
    ):
        quality = round(min(bloom3_q_score, tautology_score, a_groundedness, key_term_score, q_faithfulness), 4)
        decision = 'fail'
        print(f"    Agent 3: HARD FAIL Bloom 3 — scenario={bloom3_q_score:.2f}, tautology={tautology_score:.2f}, "
              f"ground={a_groundedness:.2f}, key_terms={key_term_score:.2f}, q_faith={q_faithfulness:.2f}")
        if user_id is not None:
            log = Agent3EvaluationLog(
                request_id=request_id, user_id=user_id, document_id=document_id,
                plan_item_id=plan_item_id, attempt=attempt,
                decision=decision, terminal_status=decision,
                quality_score=quality, reasons_json=json.dumps(reasons),
                target_bloom=bloom_key, generated_bloom=bloom_key,
                validated_bloom=bloom_key, bloom_match_type='strict_match',
                source_faithfulness_score=round(q_faithfulness, 4),
                scoreability_score=round(bloom_verb_score, 4),
            )
            db.session.add(log)
        return decision, quality

    # Hard fail: hai ý (hoặc hơn) gần nghĩa — B4-6 nới hơn vì phân tích/đánh giá có thể cùng chủ đề
    overlap_fail = max_point_overlap >= (0.58 if bloom_num >= 4 else 0.50)
    diversity_fail = diversity_score < (0.22 if bloom_num >= 4 else 0.30)
    if overlap_fail or diversity_fail:
        quality = round(min(diversity_score, 1.0 - max_point_overlap), 4)
        decision = 'fail'
        print(f"    Agent 3: HARD FAIL — ý đáp án trùng/gần nghĩa (diversity={diversity_score:.2f}, max_overlap={max_point_overlap:.2f})")
        if user_id is not None:
            log = Agent3EvaluationLog(
                request_id=request_id, user_id=user_id, document_id=document_id,
                plan_item_id=plan_item_id, attempt=attempt,
                decision=decision, terminal_status=decision,
                quality_score=quality, reasons_json=json.dumps(reasons),
                target_bloom=bloom_key, generated_bloom=bloom_key,
                validated_bloom=bloom_key, bloom_match_type='strict_match',
                source_faithfulness_score=round(q_faithfulness, 4),
                scoreability_score=round(bloom_verb_score, 4),
            )
            db.session.add(log)
        return decision, quality

    # ── Composite score ────────────────────────────────────────────────────────
    # Bloom 1-4: ưu tiên n-gram groundedness (đáp án factual)
    # Bloom 5:   bloom_verb + concept overlap
    # Bloom 6:   thêm trọng số sáng tạo (answer_creative_score)
    if bloom_num == 6:
        quality = (q_faithfulness          * 0.18
                   + a_groundedness        * 0.23
                   + bloom_verb_score      * 0.27
                   + answer_creative_score * 0.22
                   + diversity_score       * 0.10)
    elif bloom_num == 5:
        quality = (q_faithfulness  * 0.22
                   + a_groundedness * 0.36
                   + bloom_verb_score * 0.32
                   + diversity_score * 0.10)
    elif bloom_num == 3:
        quality = (a_groundedness   * 0.36
                   + key_term_score * 0.18
                   + q_faithfulness * 0.13
                   + bloom3_q_score * 0.10
                   + tautology_score * 0.08
                   + diversity_score * 0.10
                   + bloom_verb_score * 0.05)
    else:
        quality = (q_faithfulness  * 0.22
                   + a_groundedness * 0.50
                   + bloom_verb_score * 0.18
                   + diversity_score * 0.10)
    quality = max(0.0, min(round(quality, 4), 1.0))

    pass_threshold = 0.45 if bloom_num >= 5 else 0.50
    decision = 'pass' if quality >= pass_threshold else 'fail'

    if user_id is not None:
        log = Agent3EvaluationLog(
            request_id=request_id, user_id=user_id, document_id=document_id,
            plan_item_id=plan_item_id, attempt=attempt,
            decision=decision, terminal_status=decision,
            quality_score=quality, reasons_json=json.dumps(reasons),
            target_bloom=bloom_key, generated_bloom=bloom_key,
            validated_bloom=bloom_key, bloom_match_type='strict_match',
            source_faithfulness_score=round(q_faithfulness, 4),
            scoreability_score=round(bloom_verb_score, 4),
        )
        db.session.add(log)

    print(f"    Agent 3: {decision} (q={quality:.3f}, q_faith={q_faithfulness:.3f}, a_ground={a_groundedness:.3f}, bloom_verb={has_bloom_verb}, diversity={diversity_score:.2f}"
          + (f", b3_scenario={bloom3_q_score:.2f}, tautology={tautology_score:.2f}, key_terms={key_term_score:.2f}" if bloom_num == 3 else "") + ")")
    return decision, quality


def classify_bloom_exact(text: str) -> tuple[int, str]:
    """Phân loại cấp độ Bloom CHÍNH XÁC mà đoạn văn thể hiện (không phải ceiling).
    Dùng cho thực nghiệm đánh giá độ chính xác của hệ thống.
    Trả về: (bloom_level 1–6, lý_do ngắn)
    """
    if not text or len(text.strip()) < 20:
        return 1, 'too_short'

    prompt = (
        "Phân loại đoạn văn sau theo thang Bloom. Chọn MỘT cấp độ duy nhất.\n\n"
        "ĐỊNH NGHĨA VÀ DẤU HIỆU PHÂN BIỆT:\n\n"
        "1 - NHỚ: Đoạn CHỈ nêu/liệt kê sự kiện, định nghĩa, đặc điểm, thành phần — không giải thích tại sao.\n"
        "   Dấu hiệu: 'là...', 'gồm có...', 'có chức năng...', 'bao gồm...', liệt kê các loại/thành phần.\n"
        "   PHÂN BIỆT VỚI B2: Nếu đoạn KHÔNG có từ 'vì/do/giúp/khiến/bởi vì/để' giải thích cơ chế → B1.\n\n"
        "2 - HIỂU: Đoạn GIẢI THÍCH một mối quan hệ nhân quả ĐƠN GIẢN (A gây ra B), giải thích lợi ích/tác dụng.\n"
        "   Dấu hiệu: 'vì...nên...', 'do...dẫn đến...', 'giúp...', 'khiến...', 'có nghĩa là...'.\n"
        "   PHÂN BIỆT VỚI B4: Nếu chỉ có 1 chuỗi nhân quả đơn giản (A→B) → B2. Nhiều yếu tố → B4.\n\n"
        "3 - VẬN DỤNG: Đoạn mô tả AI/người ÁP DỤNG kiến thức/kỹ năng vào TÌNH HUỐNG CỤ THỂ nhưng KHÔNG tạo ra SẢN PHẨM MỚI.\n"
        "   Dấu hiệu: dùng công thức/phương pháp/quy trình vào bài toán cụ thể, thực hiện một nhiệm vụ đã biết.\n"
        "   PHÂN BIỆT VỚI B6: Nếu có SẢN PHẨM MỚI được tạo ra (app, thiết bị, website, mô hình...) → B6, không phải B3.\n\n"
        "4 - PHÂN TÍCH: Đoạn phân tích MỐI QUAN HỆ PHỨC TẠP giữa nhiều yếu tố, nhiều nguyên nhân cùng tác động, hoặc\n"
        "   mô tả tác động của X lên nhiều khía cạnh khác nhau (xã hội, kinh tế, môi trường...).\n"
        "   Dấu hiệu: nhiều yếu tố → một kết quả; hoặc một yếu tố → nhiều hậu quả; 'mối quan hệ giữa...'.\n"
        "   PHÂN BIỆT VỚI B2: B2 = 1 nguyên nhân giải thích đơn giản. B4 = phân tích đa chiều/nhiều yếu tố.\n\n"
        "5 - ĐÁNH GIÁ: Đoạn đưa ra NHẬN XÉT có lập luận, so sánh ưu/nhược, biện luận lợi/hại, có quan điểm.\n"
        "   Dấu hiệu: 'tuy nhiên...', 'trong khi...', 'ưu điểm...nhược điểm...', 'tốt hơn vì...', phán xét.\n"
        "   CHÚ Ý: Đoạn ngắn vẫn là B5 nếu CÓ SO SÁNH HAI VẾ hoặc nêu cả ưu lẫn nhược điểm.\n\n"
        "6 - SÁNG TẠO: Đoạn mô tả THIẾT KẾ/XÂY DỰNG/CHẾ TẠO/PHÁT TRIỂN một SẢN PHẨM, HỆ THỐNG, ỨNG DỤNG MỚI.\n"
        "   Dấu hiệu: 'thiết kế...', 'xây dựng...', 'chế tạo...', 'phát triển...', 'tạo ra...', có SẢN PHẨM ĐẦU RA cụ thể.\n"
        "   QUY TẮC QUAN TRỌNG: Nếu đoạn mô tả ai đó TẠO RA thứ chưa tồn tại (app, thiết bị, website, mô hình...) → B6.\n"
        "   Đây KHÔNG phải B3 dù có 'áp dụng kiến thức'. Sự khác biệt: B3 dùng thứ có sẵn, B6 tạo thứ mới.\n\n"
        "QUY TẮC TIE-BREAK khi không chắc:\n"
        "- Có sản phẩm mới được tạo ra? → B6\n"
        "- Có so sánh 2 phương án trở lên? → B5\n"
        "- Nhiều yếu tố cùng tác động? → B4\n"
        "- Giải thích 1 nguyên nhân đơn giản? → B2\n"
        "- Chỉ nêu sự kiện, không giải thích? → B1\n\n"
        f"Đoạn văn:\n\"{text}\"\n\n"
        "Trả lời theo định dạng: <số> | <lý do 1 câu>\n"
        "Chỉ trả lời 1 dòng duy nhất, bắt đầu bằng số 1-6:"
    )

    try:
        response = ai_client.chat.completions.create(
            model=_cfg.QUESTION_MODEL,
            messages=[
                {"role": "system", "content":
                 "You are a Bloom taxonomy classifier. "
                 "Reply with EXACTLY ONE line: <number 1-6> | <one-sentence reason>. "
                 "No other text allowed."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=80,
            timeout=15,
        )
        result = response.choices[0].message.content.strip()
        # Strip markdown bold mà GPT thêm vào (VD: **3** | lý do)
        result_clean = re.sub(r'\*+', '', result).strip()
        m = re.match(r'([1-6])\s*[|\-\u2013\u2014]\s*(.+)', result_clean)
        if m:
            return int(m.group(1)), m.group(2).strip()
        # GPT có thể trả lời nhiều dòng – tìm số ở dòng đầu
        first_line = result_clean.splitlines()[0].strip() if result_clean else ''
        m2 = re.match(r'^([1-6])', first_line)
        if m2:
            reason = first_line[1:].lstrip(' |-\u2013\u2014').strip() or result_clean[:80]
            return int(m2.group(1)), reason
        # fallback: tìm số bất kỳ
        m3 = re.search(r'[1-6]', result_clean)
        if m3:
            return int(m3.group()), result_clean[:80]
    except Exception as e:
        print(f"classify_bloom_exact lỗi: {str(e)[:60]}")

    # Heuristic fallback dựa vào từ khóa hành động
    t = text.lower()
    if any(w in t for w in ['thiết kế', 'xây dựng', 'phát triển', 'chế tạo', 'tạo ra', 'sáng tạo']):
        return 6, 'heuristic_sáng_tạo'
    if any(w in t for w in ['đánh giá', 'ưu điểm', 'nhược điểm', 'tuy nhiên', 'hạn chế', 'lợi thế']):
        return 5, 'heuristic_đánh_giá'
    if any(w in t for w in ['ảnh hưởng', 'nguyên nhân', 'dẫn đến', 'liên quan', 'tác động', 'khiến']):
        return 4, 'heuristic_phân_tích'
    if any(w in t for w in ['áp dụng', 'sử dụng', 'thực hiện', 'triển khai', 'vận dụng']):
        return 3, 'heuristic_vận_dụng'
    if any(w in t for w in ['giúp', 'vì', 'do', 'bởi', 'giải thích', 'có nghĩa']):
        return 2, 'heuristic_hiểu'
    return 1, 'heuristic_nhớ'


def run_agent_pipeline(content, extraction_stats, bloom_configs, question_count, algo_type,
                       user_id, document_id, use_ocr=False, progress_callback=None,
                       _chapter_map_out=None):
    """Orchestrator chính điều phối toàn bộ 3-Agent pipeline.
    Luồng: Phân tích tài liệu → với mỗi câu cần sinh:
      A1 duyệt section theo thứ tự chương → A2 sinh Q&A → A3 đánh giá
      (A2↔A3 tối đa 5 lần; nếu vẫn fail → bỏ câu đó)
    Tham số:
      content          : toàn bộ text PDF đã trích xuất
      extraction_stats : thống kê từ bước đọc PDF (page_boundaries...)
      bloom_configs    : list cấu hình Bloom người dùng chọn
                         VD: [{'bloom_level':'Bloom 2','count':3,'points':1.5}, ...]
      question_count   : tổng số câu cần sinh
      progress_callback: hàm callback(pct, msg) để cập nhật tiến độ UI
      _chapter_map_out : dict tùy chọn — nếu truyền vào sẽ được cập nhật với
                         toàn bộ chapter_content_map sau khi parse xong tài liệu
                         (dùng cho experiment, không ảnh hưởng app chính)
    Trả về: list dict kết quả Q&A
    """
    def _progress(pct, msg):
        # Gọi callback cập nhật % tiến độ lên UI (nếu có)
        if progress_callback:
            progress_callback(pct, msg)

    request_id       = f"req_{int(time.time() * 1000)}_{user_id}"  # ID duy nhất cho mỗi lần xử lý
    max_gen_attempts = 5  # số lần A2→A3 được thử lại trên cùng 1 section

    print("\n" + "=" * 80)
    print(f"🚀 NEW 3-AGENT PIPELINE: {request_id}")
    print(f"   Questions: {question_count}, User: {user_id}, Doc: {document_id}")
    print("=" * 80)

    # ── Bước 0: Phân tích tài liệu → danh sách các mục theo thứ tự ───────────
    _progress(5, 'Đang phân tích tài liệu...')
    page_boundaries = extraction_stats.get('page_boundaries', []) if extraction_stats else []
    all_sections = split_document_into_sections(content, page_boundaries=page_boundaries)

    # Lọc chỉ giữ section hợp lệ: có số mục (1.1, 2.3...) hoặc Chương/Phần/Bài N
    valid_sections = []
    for sec in all_sections:
        title = sec['title']
        has_num     = bool(re.match(r'^\d+\.\d+', title))                            # dạng '1.2'
        is_chapter  = bool(re.match(r'^(Chương|CHƯƠNG|Phần|PHẦN)', title, re.IGNORECASE))  # 'Chương 3'
        is_bai      = bool(re.match(r'^(Bài|BÀI|Bai|BAI)\s+\d+', title, re.IGNORECASE))   # 'Bài 1'
        is_fallback = bool(re.match(r'^(Đoạn|Trang) \d+', title))                   # fallback khi PDF không có mục
        if has_num or is_chapter or is_bai or is_fallback:
            valid_sections.append(sec)

    if not valid_sections and all_sections:
        # Không lọc được section nào → dùng tất cả (PDF không có tiêu đề rõ ràng)
        valid_sections = all_sections

    if not valid_sections:
        print("❌ Không tìm thấy mục nào trong tài liệu")
        db.session.commit()
        return []

    def _section_sort_key(sec):
        """Key sắp xếp section theo thứ tự số chương/mục (Chương 1 → Chương 2...)"""
        t = sec.get('title', '')
        m = re.match(r'^(\d+)\.(\d+)', t)   # dạng '2.3' → (2, 3)
        if m: return (int(m.group(1)), int(m.group(2)))
        m2 = re.match(r'^(?:Chương|Phần|Bài)\s+(\d+)', t, re.IGNORECASE)  # 'Chương 2' → (2, 0)
        if m2: return (int(m2.group(1)), 0)
        m3 = re.match(r'^(?:Đoạn|Trang)\s+(\d+)', t, re.IGNORECASE)  # 'Đoạn 12' → (12, 0)
        if m3: return (int(m3.group(1)), 0)
        return (999, 0)  # không xác định được → xếp cuối

    sorted_sections = sorted(valid_sections, key=_section_sort_key)  # đã sắp xếp Chương 1 → N
    print(f"  📄 Tìm thấy {len(sorted_sections)} mục trong tài liệu")

    # ── Xây dựng bản đồ nội dung toàn chương ─────────────────────────────────
    # chapter_content_map[chapter_key] = toàn bộ text của chương đó (gộp từ các mục)
    # Khi Agent 2 sinh câu hỏi cho mục 1.3, nó sẽ đọc cả Chương 1 để hiểu ngữ cảnh
    chapter_content_map = {}
    for _sec in sorted_sections:
        _ck = _sec.get('chapter') or 'Nội dung'
        if _ck not in chapter_content_map:
            chapter_content_map[_ck] = ''
        chapter_content_map[_ck] += '\n\n' + _sec['content']
    for _ck in chapter_content_map:
        chapter_content_map[_ck] = chapter_content_map[_ck].strip()
    print(f"  📚 Đã gộp nội dung {len(chapter_content_map)} chương làm ngữ cảnh cho Agent 2")

    # Xuất chapter_content_map ra ngoài nếu caller yêu cầu (dùng cho experiment)
    if _chapter_map_out is not None:
        _chapter_map_out.clear()
        _chapter_map_out.update(chapter_content_map)

    # ── Bước 1: Xây dựng danh sách mục tiêu (bloom × count) ──────────────────
    # targets: list các câu cần sinh, mỗi phần tử = 1 câu với bloom_level và điểm
    targets = []
    for cfg in bloom_configs:
        for _ in range(cfg.get('count', 0)):  # lặp đúng số lần = số câu yêu cầu
            targets.append({
                'bloom_level': cfg['bloom_level'],  # VD: 'Bloom 3 (Vận dụng)'
                'points':      cfg.get('points'),   # điểm người dùng nhập, None = dùng mặc định
            })

    # Điểm mặc định theo Bloom nếu người dùng không nhập
    default_points_map = {
        'Bloom 1': 1.0, 'Bloom 2': 1.5, 'Bloom 3': 2.0,
        'Bloom 4': 2.5, 'Bloom 5': 3.0, 'Bloom 6': 3.5,
    }

    results               = []           # danh sách Q&A đã sinh thành công
    start_pipeline        = time.time()  # thời điểm bắt đầu để tính tổng thời gian
    total_targets         = len(targets) # tổng số câu cần sinh
    used_section_indices  = set()        # index section đã dùng thành công → KHÔNG dùng lại

    # ── Vòng lặp chính: mỗi câu cần sinh ─────────────────────────────────────
    for target_idx, target in enumerate(targets):
        bloom_level  = target['bloom_level']
        custom_points = target['points']
        plan_item_id = f'plan_{target_idx + 1}'
        item_start   = time.time()

        bloom_key = bloom_level.split('(')[0].strip()
        points = custom_points if custom_points else default_points_map.get(bloom_key, 1.0)
        required_points = int(points / 0.25)

        pct = 15 + int((target_idx / max(total_targets, 1)) * 75)
        _progress(pct, f'Đang sinh câu {target_idx + 1}/{total_targets} ({bloom_level})...')

        print(f"\n{'─' * 60}")
        print(f"📋 {plan_item_id}: {bloom_level} — {required_points} ý ({points}đ)")
        print(f"{'─' * 60}")

        item_success = False  # cờ đánh dấu câu này đã sinh thành công chưa
        sections_tried = 0  # số sections đã thực sự thử A2→A3 (đã qua A1)
        max_sections_per_q = 4  # tối đa 4 sections/câu để tránh quá chậm

        # Duyệt section theo thứ tự: chỉ những section chưa dùng thành công
        # → section đã sinh được câu hỏi sẽ bị loại hoàn toàn, không quay lại
        # Với đoạn ngắn: ưu tiên sections đã được pre-classify đúng bloom target (nhanh hơn)
        try:
            bloom_num_target = int(bloom_key.replace('Bloom ', ''))
        except Exception:
            bloom_num_target = 0

        # Tách: sections đã biết ceiling → sort: exact match trước, gần đúng sau
        # Sections chưa biết ceiling → đưa vào sau (sẽ classify khi cần)
        known_exact   = [i for i in range(len(sorted_sections))
                         if i not in used_section_indices
                         and 'bloom_ceiling' in sorted_sections[i]
                         and sorted_sections[i]['bloom_ceiling'] == bloom_num_target]
        known_adjacent = [i for i in range(len(sorted_sections))
                          if i not in used_section_indices
                          and 'bloom_ceiling' in sorted_sections[i]
                          and sorted_sections[i]['bloom_ceiling'] != bloom_num_target]
        unknown       = [i for i in range(len(sorted_sections))
                         if i not in used_section_indices
                         and 'bloom_ceiling' not in sorted_sections[i]]
        section_order = known_exact + unknown + known_adjacent

        # Fallback: khi section pool cạn kiệt (PDF ít chương, không có sub-section)
        # → cho phép dùng lại section đã dùng, ưu tiên ceiling gần target nhất
        # Thường xảy ra với Bloom 5-6 khi tất cả section đã bị B1-B4 dùng hết
        if not section_order:
            print(f"  ♻️ Section pool cạn — fallback: cho phép dùng lại section (Bloom {bloom_num_target})")
            section_order = sorted(
                range(len(sorted_sections)),
                key=lambda i: abs(
                    (sorted_sections[i].get('bloom_ceiling') or 3) - bloom_num_target
                ),
            )

        for sec_idx in section_order:
            if item_success:
                break

            section         = sorted_sections[sec_idx]
            section_title   = section.get('title', 'Nội dung')  # tiêu đề mục VD: "1.3 Khái niệm"
            section_content = section.get('content', '')         # nội dung riêng của mục

            # ── Lọc section quá ngắn / chỉ là đề mục tổng quan ──────────────
            # Section có nội dung < 150 chars thường chỉ là heading chapter hoặc TOC
            # → không đủ chất liệu để sinh câu hỏi có nghĩa
            _min_content = 150 if bloom_num_target >= 2 else 80
            if len(section_content.strip()) < _min_content:
                print(f"  ⏭️ Bỏ qua section quá ngắn ({len(section_content.strip())}c < {_min_content}c): {section_title[:60]}")
                continue

            # Lấy toàn bộ nội dung chương mà mục này thuộc về
            # → Agent 2 đọc hết chương để hiểu ngữ cảnh, rồi sinh câu hỏi đúng mục
            chapter_key     = section.get('chapter') or 'Nội dung'
            chapter_content = chapter_content_map.get(chapter_key, section_content)

            print(f"\n  📂 Thử mục: {section_title[:60]} | ngữ cảnh: {chapter_key} ({len(chapter_content)} ký tự)")

            # ── Lazy bloom ceiling: chỉ gọi AI khi mục này được chọn thử ────
            # Kết quả cache trong section['bloom_ceiling'] → không tính lại nếu mục được dùng lần 2
            if 'bloom_ceiling' not in section:
                section['bloom_ceiling'] = _get_section_bloom_ceiling(section_content, section_title)
                print(f"    🧠 Ngữ nghĩa: Bloom ≤ {section['bloom_ceiling']} | {section_title[:50]}")

            # ── Agent 1: Kiểm tra tính khả thi Bloom (dùng nội dung mục lẻ) ──
            feasible, a1_quality, _ = new_agent1_bloom_feasibility(
                section_content, section_title, bloom_level,
                request_id, user_id, document_id, plan_item_id,
                bloom_ceiling=section['bloom_ceiling'],
            )
            if not feasible:
                print(f"  ⛔ Agent 1: Mục không phù hợp cho {bloom_key} → bỏ qua")
                continue

            if sections_tried >= max_sections_per_q:
                print(f"  ⛔ Đã thử {sections_tried} sections → dừng tìm kiếm cho câu {plan_item_id}")
                break
            sections_tried += 1

            # ── Agent 2 → Agent 3 loop ────────────────────────────────────────
            for gen_attempt in range(1, max_gen_attempts + 1):
                print(f"  🔄 Agent 2 lần {gen_attempt}/{max_gen_attempts}")

                # Agent 2 nhận section_content làm nguồn chính (bám sát nội dung mục)
                # chapter_content truyền qua chapter_context để hiểu bối cảnh chương
                question, answer, model_used = new_agent2_generate_qa(
                    section_content, section_title, bloom_level, required_points,
                    request_id, user_id, document_id, plan_item_id, attempt=gen_attempt,
                    chapter_context=chapter_content,
                )

                if not question or not answer:
                    print(f"  ❌ Agent 2 không sinh được Q&A")
                    continue

                # Agent 3 đánh giá groundedness cũng dựa trên chapter_content
                a3_decision, a3_quality = new_agent3_evaluate_qa(
                    question, answer, chapter_content, section_title, bloom_level,
                    request_id, user_id, document_id, plan_item_id, attempt=gen_attempt,
                )

                if a3_decision == 'pass':
                    item_success = True
                    used_section_indices.add(sec_idx)  # section này đã dùng → loại khỏi pool

                    total_pts, sub_pts, breakdown = calculate_points_from_bloom(bloom_level, custom_points)

                    # Xây dựng section_info hiển thị trên UI
                    sec_num       = extract_section_number(section_title)
                    display_title = clean_section_title(section_title)
                    chapter       = section.get('chapter', 'Nội dung')

                    if sec_num and display_title.startswith(sec_num):
                        display_title = display_title[len(sec_num):].strip().lstrip(':').strip()
                    display_title = re.sub(r'^Chương\s*\d+\s*[:.]?\s*', '', display_title, flags=re.IGNORECASE).strip()
                    display_title = re.sub(r'^(Bài|BÀI)\s+\d+[:\.\s]+\s*', '', display_title, flags=re.IGNORECASE).strip()
                    if not display_title:
                        display_title = section_title

                    if sec_num:
                        section_info = f"{chapter} - Mục {sec_num}: {display_title}"
                    elif section.get('page_num'):
                        section_info = f"Trang {section['page_num']}: {display_title}"
                    else:
                        section_info = f"{chapter}: {display_title}"

                    results.append({
                        'question':         question,
                        'answer':           answer,
                        'bloom_level':      bloom_level,
                        'algorithm':        'TEXTQAI',
                        'section_info':     section_info,
                        'total_points':     total_pts,
                        'sub_points_count': sub_pts,
                        'points_breakdown': breakdown,
                        'process_time':     round(time.time() - item_start, 2),
                        'section_content':  section_content,   # nội dung MỤC cụ thể (ngắn, dùng cho BLEU-4 section)
                        'chapter_content':  chapter_content,   # toàn bộ nội dung CHƯƠNG (dùng cho BLEU-4 chapter)
                        'chapter_key':      chapter_key,        # tên chương VD: "Chương 1"
                    })
                    print(f"  ✅ {plan_item_id}: Sinh thành công Q&A!")
                    break
                else:
                    print(f"  ↩️ Agent 3 từ chối (q={a3_quality:.3f}) → Agent 2 sinh lại...")

            # A2→A3 fail hết max_gen_attempts lần trên mục này → thử mục khác
            if not item_success:
                print(f"  ⛔ A2→A3 thất bại hết {max_gen_attempts} lần trên '{section_title[:50]}' → thử mục tiếp ({sections_tried}/{max_sections_per_q})")
                continue  # thử section tiếp theo thay vì bỏ câu

        if not item_success:
            print(f"  ⚠️ {plan_item_id}: Không sinh được câu hỏi")

        # Delay 2 giây giữa các câu để tránh rate-limit API
        if target_idx < total_targets - 1:
            time.sleep(2)

    if user_id is not None:
        db.session.commit()

    _progress(98, f'Hoàn tất! Đã sinh {len(results)}/{total_targets} câu hỏi.')
    total_time = round(time.time() - start_pipeline, 2)
    print(f"\n{'=' * 80}")
    print(f"✅ NEW PIPELINE COMPLETE: {len(results)}/{total_targets} items in {total_time}s")
    print(f"{'=' * 80}")

    return results


