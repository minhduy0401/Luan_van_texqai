# utils/app_settings.py – Đọc cấu hình runtime từ system_settings (DB)
from flask import has_app_context

SETTING_DEFAULTS = {
    'allow_register': '1',
    'default_credits': '5',
    'enable_ocr': '0',
    'active_ai_provider': 'openrouter',
    'ai_model': 'google/gemini-2.5-flash-lite',
    'openrouter_model': 'google/gemini-2.5-flash-lite',
    'openai_model': 'gpt-4o-mini',
    'gemini_model': 'gemini-2.5-flash',
    'vnpay_url': 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html',
    'enable_vnpay': '1',
    'enable_bank_transfer': '1',
    'smtp_port': '587',
    'smtp_sender_name': 'TEXTQAI Support',
    'captcha_type': 'none',
    'site_name': 'TEXTQAI',
    'site_title_vi': 'Hệ thống sinh câu hỏi tự động',
    'site_title_en': 'Automatic Question Generation System',
    'site_description_vi': (
        'Hệ thống sinh câu hỏi tự động theo thang Bloom — hỗ trợ giảng viên tạo đề thi nhanh, '
        'chính xác và đúng chuẩn giáo dục từ tài liệu PDF.'
    ),
    'site_description_en': (
        "Automatic question generation based on Bloom's taxonomy — helping educators build tests "
        'rapidly, accurately, and aligned with standard pedagogy from PDF documents.'
    ),
    'site_logo': '',
    'site_favicon': '',
    'site_branding_version': '1',
}


def get_setting(key: str, default=None) -> str:
    if default is None:
        default = SETTING_DEFAULTS.get(key, '')
    if not has_app_context():
        return str(default)
    try:
        from models import SystemSetting
        return SystemSetting.get(key, default)
    except Exception:
        return str(default)


def get_secret_key(fallback: str) -> str:
    sk = get_setting('secret_key', '').strip()
    return sk or fallback


def get_vnpay_config() -> dict:
    return {
        'tmn_code': get_setting('vnpay_tmn_code', '').strip(),
        'hash_secret': get_setting('vnpay_hash_secret', '').strip(),
        'url': get_setting('vnpay_url', SETTING_DEFAULTS['vnpay_url']).strip(),
        'return_url': get_setting('vnpay_return_url', '').strip(),
    }


def get_google_oauth_config() -> dict:
    return {
        'client_id': get_setting('google_client_id', '').strip(),
        'client_secret': get_setting('google_client_secret', '').strip(),
        'redirect_uri': get_setting('google_redirect_uri', '').strip(),
    }


def get_sepay_api_key() -> str:
    return get_setting('sepay_api_key', '').strip()


def seed_default_settings(db_session, SystemSetting) -> int:
    """Insert missing default keys into system_settings. Returns count added."""
    added = 0
    for key, value in SETTING_DEFAULTS.items():
        if not SystemSetting.query.get(key):
            db_session.add(SystemSetting(key=key, value=str(value)))
            added += 1
    if added:
        db_session.commit()
    return added
