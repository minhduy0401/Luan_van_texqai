#!/usr/bin/env python3
"""Import cấu hình từ file .env (nếu có) vào bảng system_settings.

Chạy một lần khi chuyển từ .env sang database:
    python migrate_env_to_db.py

Sau đó có thể xóa hoặc bỏ qua file .env.
"""
import os
import re

ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')

# Map biến .env → key system_settings
ENV_TO_SETTING = {
    'SECRET_KEY': 'secret_key',
    'OPENROUTER_API_KEY': 'openrouter_api_key',
    'OPENAI_API_KEY': 'openai_api_key',
    'GEMINI_API_KEY': 'gemini_api_key',
    'QUESTION_MODEL': 'ai_model',
    'ANSWER_MODEL': 'ai_model',
    'ENABLE_OCR': 'enable_ocr',
    'GOOGLE_CLIENT_ID': 'google_client_id',
    'GOOGLE_CLIENT_SECRET': 'google_client_secret',
    'GOOGLE_REDIRECT_URI': 'google_redirect_uri',
    'SEPAY_API_KEY': 'sepay_api_key',
    'BANK_BIN': 'bank_bin',
    'BANK_ACCOUNT': 'bank_account',
    'BANK_HOLDER': 'bank_holder',
    'BANK_BRANCH': 'bank_branch',
    'VNPAY_TMN_CODE': 'vnpay_tmn_code',
    'VNPAY_HASH_SECRET': 'vnpay_hash_secret',
    'VNPAY_URL': 'vnpay_url',
    'VNPAY_RETURN_URL': 'vnpay_return_url',
}


def _parse_env_file(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    out = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val:
                out[key] = val
    return out


def main():
    env_vars = _parse_env_file(ENV_PATH)
    if not env_vars:
        print(f'ℹ️  Không tìm thấy giá trị trong {ENV_PATH}')
        return

    from app import app, db
    from models import SystemSetting
    from utils.app_settings import seed_default_settings
    import config as cfg_module

    imported = 0
    with app.app_context():
        seed_default_settings(db.session, SystemSetting)
        for env_key, setting_key in ENV_TO_SETTING.items():
            val = env_vars.get(env_key, '').strip()
            if not val:
                continue
            current = SystemSetting.get(setting_key, '').strip()
            if current and (setting_key.endswith('_key') or 'secret' in setting_key):
                print(f'  ⏭️  {setting_key}: đã có trong DB, bỏ qua')
                continue
            SystemSetting.set(setting_key, val)
            imported += 1
            print(f'  ✅ {env_key} → {setting_key}')

        if env_vars.get('QUESTION_MODEL'):
            cfg_module.sync_from_db()

    print(f'\n🎉 Đã import {imported} mục vào system_settings.')
    print('   Kiểm tra Admin → Cài đặt hệ thống, sau đó có thể bỏ file .env.')


if __name__ == '__main__':
    main()
