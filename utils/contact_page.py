# utils/contact_page.py – Cấu hình trang liên hệ (file JSON, không qua database)
import json
import os
import re

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_FILE = os.path.join(_PROJECT_ROOT, 'instance', 'contact_page.json')

DEFAULT_CONTACT = {
    'support_email': 'duy226466@nctu.edu.vn',
    'phone_display': '+84 93 118 3550',
    'phone_tel': '+84931183550',
    'address_vi': 'Trường Đại học Nam Cần Thơ',
    'address_en': 'Nam Can Tho University',
    'facebook_url': 'https://www.facebook.com/babyduytv0401/',
    'github_url': 'https://github.com/minhduy0401',
    'hours_vi': 'Thứ 2–6 · 8:00–17:00 (GMT+7)',
    'hours_en': 'Mon–Fri · 8:00–17:00 (GMT+7)',
    'response_vi': 'Phản hồi trong 1–2 ngày làm việc',
    'response_en': 'Response within 1–2 business days',
    'footer_desc_vi': (
        'Hệ thống sinh câu hỏi tự động theo thang Bloom — hỗ trợ giảng viên tạo đề thi nhanh, '
        'chính xác và đúng chuẩn giáo dục.'
    ),
    'footer_desc_en': (
        'Automatic question generation based on Bloom taxonomy — helping educators build tests '
        'rapidly, accurately, and aligned with standard pedagogy.'
    ),
}

_ALLOWED_KEYS = frozenset(DEFAULT_CONTACT.keys())


def _normalize_phone_tel(display: str, tel: str) -> str:
    tel = (tel or '').strip()
    if tel:
        return tel
    digits = re.sub(r'[^\d+]', '', display or '')
    return digits or ''


def get_contact_config() -> dict:
    """Đọc cấu hình liên hệ (merge với mặc định)."""
    data = dict(DEFAULT_CONTACT)
    try:
        if os.path.isfile(_CONFIG_FILE):
            with open(_CONFIG_FILE, encoding='utf-8') as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                for key in _ALLOWED_KEYS:
                    if key in stored and stored[key] is not None:
                        data[key] = str(stored[key]).strip()
    except (OSError, json.JSONDecodeError):
        pass
    data['phone_tel'] = _normalize_phone_tel(data.get('phone_display', ''), data.get('phone_tel', ''))
    return data


def get_contact_for_lang(lang: str = 'vi') -> dict:
    """Trả về contact kèm trường theo ngôn ngữ hiện tại."""
    cfg = get_contact_config()
    en = lang == 'en'
    return {
        **cfg,
        'address': cfg['address_en'] if en else cfg['address_vi'],
        'hours': cfg['hours_en'] if en else cfg['hours_vi'],
        'response_note': cfg['response_en'] if en else cfg['response_vi'],
        'footer_desc': cfg['footer_desc_en'] if en else cfg['footer_desc_vi'],
    }


def save_contact_config(form: dict) -> None:
    """Ghi cấu hình từ form admin."""
    out = {}
    for key in _ALLOWED_KEYS:
        out[key] = (form.get(key) or DEFAULT_CONTACT.get(key, '')).strip()

    email = out.get('support_email', '')
    if not email or '@' not in email:
        raise ValueError('Email hỗ trợ không hợp lệ.')

    out['phone_tel'] = _normalize_phone_tel(out.get('phone_display', ''), out.get('phone_tel', ''))

    for url_key in ('facebook_url', 'github_url'):
        url = out.get(url_key, '')
        if url and not url.startswith(('http://', 'https://')):
            raise ValueError(f'URL {url_key} phải bắt đầu bằng http:// hoặc https://')

    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
    tmp = _CONFIG_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _CONFIG_FILE)
