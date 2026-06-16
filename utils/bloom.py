# utils/bloom.py – Bloom taxonomy level normalization helpers
import re

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
    
    # Nếu đã đúng format, return luôn
    if bloom_lower.startswith('bloom') and '(' in bloom_text:
        return bloom_text
    
    # Tìm trong map
    for key, value in bloom_map.items():
        if key in bloom_lower:
            return value
    
    # Extract số Bloom nếu có
    import re
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
