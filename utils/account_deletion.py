# utils/account_deletion.py – Yêu cầu xóa tài khoản (token file, không cần bảng mới)
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOKENS_DIR = os.path.join(_PROJECT_ROOT, 'instance', 'deletion_tokens')
_TOKEN_TTL_HOURS = 48
_RESEND_COOLDOWN_MINUTES = 15


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _token_path(token: str) -> str:
    safe = ''.join(c for c in token if c.isalnum() or c in '-_')
    if not safe or safe != token:
        raise ValueError('Token không hợp lệ')
    return os.path.join(_TOKENS_DIR, f'{safe}.json')


def _load_token(token: str) -> dict | None:
    path = _token_path(token)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _save_token(token: str, data: dict) -> None:
    os.makedirs(_TOKENS_DIR, exist_ok=True)
    path = _token_path(token)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _recent_pending_for_email(email: str) -> dict | None:
    if not os.path.isdir(_TOKENS_DIR):
        return None
    email_l = email.lower()
    cutoff = _utcnow() - timedelta(minutes=_RESEND_COOLDOWN_MINUTES)
    for name in os.listdir(_TOKENS_DIR):
        if not name.endswith('.json'):
            continue
        try:
            with open(os.path.join(_TOKENS_DIR, name), encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if data.get('email', '').lower() != email_l:
            continue
        if data.get('confirmed'):
            continue
        created = datetime.fromisoformat(data['created_at'])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created >= cutoff:
            return data
    return None


def create_deletion_request(email: str, reason: str = '', notes: str = '') -> tuple[str, dict]:
    """Tạo token yêu cầu xóa. Trả về (token, record)."""
    email = (email or '').strip().lower()
    if not email or '@' not in email:
        raise ValueError('Email không hợp lệ')

    pending = _recent_pending_for_email(email)
    if pending:
        raise ValueError('cooldown')

    token = secrets.token_urlsafe(32)
    now = _utcnow()
    record = {
        'email': email,
        'reason': (reason or '').strip()[:200],
        'notes': (notes or '').strip()[:2000],
        'created_at': now.isoformat(),
        'expires_at': (now + timedelta(hours=_TOKEN_TTL_HOURS)).isoformat(),
        'confirmed': False,
        'confirmed_at': None,
    }
    _save_token(token, record)
    return token, record


def confirm_deletion_request(token: str) -> dict:
    """Xác nhận yêu cầu. Trả về record đã cập nhật."""
    data = _load_token(token)
    if not data:
        raise ValueError('not_found')
    if data.get('confirmed'):
        return data

    expires = datetime.fromisoformat(data['expires_at'])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if _utcnow() > expires:
        raise ValueError('expired')

    data['confirmed'] = True
    data['confirmed_at'] = _utcnow().isoformat()
    _save_token(token, data)
    return data
