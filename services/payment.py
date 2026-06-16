# services/payment.py – Quản lý gói credit + xác thực SePay webhook + VNPAY
# Luồng thanh toán: user chuyển khoản → SePay phát hiện → webhook → cộng credits tự động

import os
import hmac
import hashlib
import urllib.parse
from datetime import datetime, timedelta

# ── VNPAY config ──────────────────────────────────────────────────────────────
VNPAY_TMN_CODE   = os.getenv('VNPAY_TMN_CODE', '')
VNPAY_HASH_SECRET= os.getenv('VNPAY_HASH_SECRET', '')
VNPAY_URL        = os.getenv('VNPAY_URL', 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html')
VNPAY_RETURN_URL = os.getenv('VNPAY_RETURN_URL', '')   # https://yoursite.com/payment/vnpay/return


def _vnpay_sign(params: dict) -> str:
    """Tạo chữ ký HMAC-SHA512 cho VNPAY."""
    sorted_params = sorted(params.items())
    query = '&'.join(f"{k}={urllib.parse.quote_plus(str(v), safe='')}" for k, v in sorted_params)
    return hmac.new(VNPAY_HASH_SECRET.encode('utf-8'), query.encode('utf-8'), hashlib.sha512).hexdigest()


def vnpay_create_payment_url(order_code: str, amount_vnd: int, order_info: str,
                              ip_addr: str, return_url: str) -> str:
    """Tạo URL thanh toán VNPAY."""
    now = datetime.now()
    expire = now + timedelta(minutes=15)
    params = {
        'vnp_Version':    '2.1.0',
        'vnp_Command':    'pay',
        'vnp_TmnCode':    VNPAY_TMN_CODE,
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
    secure_hash = _vnpay_sign(params)
    params['vnp_SecureHash'] = secure_hash
    return VNPAY_URL + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)


def vnpay_verify_return(params: dict) -> bool:
    """Xác minh chữ ký từ VNPAY return/IPN params."""
    received_hash = params.get('vnp_SecureHash', '')
    check_params  = {k: v for k, v in params.items()
                     if k not in ('vnp_SecureHash', 'vnp_SecureHashType')}
    expected_hash = _vnpay_sign(check_params)
    return hmac.compare_digest(received_hash.lower(), expected_hash.lower())


# Bảng giá credit (đồng bộ với frontend)
CREDIT_PACKAGES = [
    {'id': 1, 'name': 'Dùng thử',  'credits': 10,   'price_vnd': 4_000,   'is_popular': False},
    {'id': 2, 'name': 'Starter',   'credits': 50,   'price_vnd': 13_000,  'is_popular': False},
    {'id': 3, 'name': 'Standard',  'credits': 200,  'price_vnd': 40_000,  'is_popular': True},
    {'id': 4, 'name': 'Pro',       'credits': 500,  'price_vnd': 90_000,  'is_popular': False},
    {'id': 5, 'name': 'Academic',  'credits': 1500, 'price_vnd': 220_000, 'is_popular': False},
]

# Thuê bao tháng
SUBSCRIPTION_PACKAGES = [
    {'id': 10, 'name': 'Sinh viên',    'credits': 100,  'price_vnd': 39_000,  'period': 'tháng'},
    {'id': 11, 'name': 'Giảng viên',   'credits': 500,  'price_vnd': 89_000,  'period': 'tháng'},
    {'id': 12, 'name': 'Khoa/Bộ môn',  'credits': 2000, 'price_vnd': 209_000, 'period': 'tháng'},
]


def get_package_by_id(package_id: int) -> dict | None:
    """Tìm gói credit theo ID (cả credit lẻ và subscription)."""
    all_packages = CREDIT_PACKAGES + SUBSCRIPTION_PACKAGES
    return next((p for p in all_packages if p['id'] == package_id), None)
