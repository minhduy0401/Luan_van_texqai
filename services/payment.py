# services/payment.py – Quản lý gói credit + xác thực SePay webhook + VNPAY
import hmac
import hashlib
import urllib.parse
from datetime import datetime, timedelta

from utils.app_settings import get_vnpay_config


def _vnpay_sign(params: dict, hash_secret: str) -> str:
    """Tạo chữ ký HMAC-SHA512 cho VNPAY."""
    sorted_params = sorted(params.items())
    query = '&'.join(f"{k}={urllib.parse.quote_plus(str(v), safe='')}" for k, v in sorted_params)
    return hmac.new(hash_secret.encode('utf-8'), query.encode('utf-8'), hashlib.sha512).hexdigest()


def vnpay_create_payment_url(order_code: str, amount_vnd: int, order_info: str,
                              ip_addr: str, return_url: str) -> str:
    """Tạo URL thanh toán VNPAY."""
    cfg = get_vnpay_config()
    now = datetime.now()
    expire = now + timedelta(minutes=15)
    params = {
        'vnp_Version':    '2.1.0',
        'vnp_Command':    'pay',
        'vnp_TmnCode':    cfg['tmn_code'],
        'vnp_Amount':     str(amount_vnd * 100),
        'vnp_CurrCode':   'VND',
        'vnp_TxnRef':     order_code,
        'vnp_OrderInfo':  order_info,
        'vnp_OrderType':  'other',
        'vnp_Locale':     'vn',
        'vnp_ReturnUrl':  return_url,
        'vnp_IpAddr':     ip_addr,
        'vnp_CreateDate': now.strftime('%Y%m%d%H%M%S'),
        'vnp_ExpireDate': expire.strftime('%Y%m%d%H%M%S'),
    }
    secure_hash = _vnpay_sign(params, cfg['hash_secret'])
    params['vnp_SecureHash'] = secure_hash
    return cfg['url'] + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)


def vnpay_verify_return(params: dict) -> bool:
    """Xác minh chữ ký từ VNPAY return/IPN params."""
    cfg = get_vnpay_config()
    received_hash = params.get('vnp_SecureHash', '')
    check_params  = {k: v for k, v in params.items()
                     if k not in ('vnp_SecureHash', 'vnp_SecureHashType')}
    expected_hash = _vnpay_sign(check_params, cfg['hash_secret'])
    return hmac.compare_digest(received_hash.lower(), expected_hash.lower())


def vnpay_is_configured() -> bool:
    cfg = get_vnpay_config()
    return bool(cfg['tmn_code'] and cfg['hash_secret'])


def vnpay_return_url_default() -> str:
    return get_vnpay_config()['return_url']


# Bảng giá credit (đồng bộ với frontend)
CREDIT_PACKAGES = [
    {'id': 1, 'name': 'Dùng thử',  'credits': 10,   'price_vnd': 4_000,   'is_popular': False},
    {'id': 2, 'name': 'Starter',   'credits': 50,   'price_vnd': 15_000,  'is_popular': False},
    {'id': 3, 'name': 'Standard',  'credits': 100,  'price_vnd': 19_000,  'is_popular': True},
    {'id': 4, 'name': 'Pro',       'credits': 500,  'price_vnd': 85_000,  'is_popular': False},
    {'id': 5, 'name': 'Academic',  'credits': 1500, 'price_vnd': 220_000, 'is_popular': False},
]

# Thuê bao tháng
SUBSCRIPTION_PACKAGES = [
    {'id': 10, 'name': 'Sinh viên',    'credits': 120,  'price_vnd': 29_000,  'period': 'tháng'},
    {'id': 11, 'name': 'Giảng viên',   'credits': 600,  'price_vnd': 99_000,  'period': 'tháng'},
    {'id': 12, 'name': 'Khoa/Bộ môn',  'credits': 2000, 'price_vnd': 289_000, 'period': 'tháng'},
]


def get_package_by_id(package_id: int) -> dict | None:
    """Tìm gói credit theo ID (cả credit lẻ và subscription)."""
    all_packages = CREDIT_PACKAGES + SUBSCRIPTION_PACKAGES
    return next((p for p in all_packages if p['id'] == package_id), None)
