# utils/bootstrap_config.py – Cấu hình bootstrap (chỉ kết nối DB ban đầu)
# Mọi secret/cấu hình khác lưu trong system_settings (Admin → Cài đặt).
import json
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOOTSTRAP_PATH = os.path.join(_PROJECT_ROOT, 'instance', 'bootstrap.json')

DEFAULT_DATABASE_URI = 'postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/luanvan_ai'
DEFAULT_SECRET_KEY = 'change-me-via-admin-settings'

_cache: dict | None = None


def _load_bootstrap() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    _cache = {}
    if os.path.isfile(_BOOTSTRAP_PATH):
        try:
            with open(_BOOTSTRAP_PATH, encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _cache = data
        except (json.JSONDecodeError, OSError):
            pass
    return _cache


def get_bootstrap(key: str, default=None):
    return _load_bootstrap().get(key, default)


def get_database_uri() -> str:
    return get_bootstrap('database_uri', DEFAULT_DATABASE_URI)


def get_initial_secret_key() -> str:
    return get_bootstrap('secret_key', DEFAULT_SECRET_KEY)


def bootstrap_path() -> str:
    return _BOOTSTRAP_PATH
