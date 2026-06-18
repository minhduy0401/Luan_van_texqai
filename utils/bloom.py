# utils/bloom.py – Bloom taxonomy level normalization helpers
import re
from collections import defaultdict

CANONICAL_BLOOM_LEVELS = (
    'Bloom 1 (Nhớ)',
    'Bloom 2 (Hiểu)',
    'Bloom 3 (Vận dụng)',
    'Bloom 4 (Phân tích)',
    'Bloom 5 (Đánh giá)',
    'Bloom 6 (Sáng tạo)',
)

# --- HELPER FUNCTIONS ---
def normalize_bloom_level(bloom_text):
    """Chuẩn hóa tên Bloom level về format: Bloom X (Tên tiếng Việt)"""
    if not bloom_text:
        return "Bloom 1 (Nhớ)"
    
    # Map các tên cũ/tiếng Anh sang format mới
    bloom_map = {
        'knowledge': 'Bloom 1 (Nhớ)',
        'nhớ lại': 'Bloom 1 (Nhớ)',
        'comprehension': 'Bloom 2 (Hiểu)',
        'understand': 'Bloom 2 (Hiểu)',
        'application': 'Bloom 3 (Vận dụng)',
        'apply': 'Bloom 3 (Vận dụng)',
        'ứng dụng': 'Bloom 3 (Vận dụng)',
        'áp dụng': 'Bloom 3 (Vận dụng)',
        'analysis': 'Bloom 4 (Phân tích)',
        'analyze': 'Bloom 4 (Phân tích)',
        'evaluation': 'Bloom 5 (Đánh giá)',
        'evaluate': 'Bloom 5 (Đánh giá)',
        'synthesis': 'Bloom 6 (Sáng tạo)',
        'create': 'Bloom 6 (Sáng tạo)',
        'tạo dựng': 'Bloom 6 (Sáng tạo)',
        'nhớ': 'Bloom 1 (Nhớ)',
        'hiểu': 'Bloom 2 (Hiểu)',
        'vận dụng': 'Bloom 3 (Vận dụng)',
        'phân tích': 'Bloom 4 (Phân tích)',
        'đánh giá': 'Bloom 5 (Đánh giá)',
        'sáng tạo': 'Bloom 6 (Sáng tạo)'
    }
    
    bloom_lower = bloom_text.lower().strip()
    
    # Nếu đã đúng format Bloom X (...), chuẩn hóa về tên canonical
    if bloom_lower.startswith('bloom') and '(' in bloom_text:
        match = re.search(r'bloom\s*(\d)', bloom_lower)
        if match:
            level_names = {
                '1': 'Bloom 1 (Nhớ)',
                '2': 'Bloom 2 (Hiểu)',
                '3': 'Bloom 3 (Vận dụng)',
                '4': 'Bloom 4 (Phân tích)',
                '5': 'Bloom 5 (Đánh giá)',
                '6': 'Bloom 6 (Sáng tạo)',
            }
            return level_names.get(match.group(1), bloom_text)
        return bloom_text
    
    # Tìm trong map
    for key, value in bloom_map.items():
        if key in bloom_lower:
            return value
    
    # Extract số Bloom nếu có
    match = re.search(r'bloom\s*(\d)', bloom_lower)
    if match:
        level = match.group(1)
        level_names = {
            '1': 'Bloom 1 (Nhớ)',
            '2': 'Bloom 2 (Hiểu)',
            '3': 'Bloom 3 (Vận dụng)',
            '4': 'Bloom 4 (Phân tích)',
            '5': 'Bloom 5 (Đánh giá)',
            '6': 'Bloom 6 (Sáng tạo)'
        }
        return level_names.get(level, 'Bloom 1 (Nhớ)')
    
    # Default
    return bloom_text


def aggregate_bloom_stats(raw_rows):
    """Gom Bloom theo tên chuẩn; trả về thống kê + mức dùng nhiều nhất."""
    totals = defaultdict(int)
    for level, cnt in raw_rows:
        totals[normalize_bloom_level(level)] += int(cnt or 0)

    chart_stats = [(k, totals[k]) for k in CANONICAL_BLOOM_LEVELS if totals.get(k)]
    for level, cnt in totals.items():
        if level not in CANONICAL_BLOOM_LEVELS:
            chart_stats.append((level, cnt))

    total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    top_level, top_count = ranked[0] if ranked else (None, 0)
    top_pct = round(top_count / total * 100, 1) if total else 0

    return {
        'stats': chart_stats,
        'total': total,
        'top_level': top_level,
        'top_count': top_count,
        'top_pct': top_pct,
    }


def bloom_short_label(canonical: str, lang: str = 'vi') -> str:
    """Nhãn gọn cho biểu đồ: Bloom 1 · Nhớ / Bloom 1 · Remembering."""
    from utils.translations import TRANSLATIONS
    if not canonical:
        return '—'
    text = TRANSLATIONS.get(canonical, {}).get(
        'en' if lang == 'en' else 'vi', canonical
    )
    m = re.match(r'^Bloom\s*(\d)\s*\((.+)\)\s*$', text.strip(), re.I)
    if m:
        return f"Bloom {m.group(1)} · {m.group(2)}"
    return text
