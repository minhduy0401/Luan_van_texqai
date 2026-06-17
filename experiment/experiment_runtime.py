# experiment/experiment_runtime.py – Đồng bộ cấu hình AI từ app chính (PostgreSQL) sang SQLite thực nghiệm
"""Pipeline gọi ai_client qua SystemSetting trong app context hiện tại.
Thí nghiệm dùng SQLite riêng → cần copy key/provider từ DB production trước khi chạy."""

_RUNTIME_KEYS = (
    'active_ai_provider',
    'openrouter_api_key',
    'openai_api_key',
    'gemini_api_key',
    'ai_model',
    'openrouter_model',
    'openai_model',
    'gemini_model',
    'enable_ocr',
)


def seed_settings_from_main_app(exp_app) -> int:
    """Copy system_settings từ app Flask chính vào DB SQLite của thí nghiệm."""
    from extensions import db
    from models import SystemSetting
    from utils.app_settings import seed_default_settings

    try:
        from app import app as main_app
    except Exception as exc:
        raise RuntimeError(
            'Không load được app chính — kiểm tra PostgreSQL và instance/bootstrap.json'
        ) from exc

    copied = {}
    with main_app.app_context():
        for key in _RUNTIME_KEYS:
            val = SystemSetting.get(key, '').strip()
            if val:
                copied[key] = val

    if not copied.get('openrouter_api_key') and not copied.get('openai_api_key') and not copied.get('gemini_api_key'):
        raise RuntimeError(
            'Chưa có API key trong Admin → Cài đặt (system_settings). '
            'Chạy migrate_env_to_db.py hoặc nhập key qua Admin.'
        )

    with exp_app.app_context():
        seed_default_settings(db.session, SystemSetting)
        for key, val in copied.items():
            SystemSetting.set(key, val)

    try:
        import config as cfg
        cfg.sync_from_db()
    except Exception:
        pass

    return len(copied)
