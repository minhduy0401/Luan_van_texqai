#!/usr/bin/env python3
"""Tạo toàn bộ bảng MySQL từ models.py (lần cài đặt đầu tiên).

Chạy sau khi đã:
  1. Tạo database (database/init.sql hoặc thủ công)
  2. Sao chép bootstrap.json.example → instance/bootstrap.json và sửa database_uri

Usage:
    python init_db.py
"""
import sys

from utils.bootstrap_config import get_database_uri, bootstrap_path

uri = get_database_uri()
if not uri:
    print('❌ Chưa có database_uri trong instance/bootstrap.json')
    print(f'   Tạo file: {bootstrap_path()}')
    print('   Hoặc sao chép bootstrap.json.example → instance/bootstrap.json')
    sys.exit(1)

from app import app, db
import models  # noqa: F401 — đăng ký models với SQLAlchemy
from models import SystemSetting
from utils.app_settings import seed_default_settings

TABLES = [
    'users',
    'user_auth_providers',
    'documents',
    'qa_results',
    'agent1_evaluation_logs',
    'agent2_evaluation_logs',
    'agent3_evaluation_logs',
    'credit_packages',
    'subscription_packages',
    'transactions',
    'feedbacks',
    'system_settings',
]

if __name__ == '__main__':
    print(f'🔗 DATABASE_URI: {uri.split("@")[-1] if "@" in uri else uri}')
    with app.app_context():
        db.create_all()
        seeded = seed_default_settings(db.session, SystemSetting)
        from sqlalchemy import inspect
        existing = set(inspect(db.engine).get_table_names())
    print('\n✅ db.create_all() hoàn tất. Các bảng:')
    for name in TABLES:
        mark = '✓' if name in existing else '?'
        print(f'   {mark} {name}')
    if seeded:
        print(f'\n🌱 Đã seed {seeded} cài đặt mặc định vào system_settings.')
    print('\n💡 Cấu hình API key, OAuth, VNPAY tại Admin → Cài đặt hệ thống.')
    print('   Khởi động app: python app.py')
