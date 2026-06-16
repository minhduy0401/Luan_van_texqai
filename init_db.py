#!/usr/bin/env python3
"""Tạo toàn bộ bảng MySQL từ models.py (lần cài đặt đầu tiên).

Chạy sau khi đã:
  1. Tạo database (database/init.sql hoặc thủ công)
  2. Cấu hình DATABASE_URI trong file .env

Usage:
    python init_db.py
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

uri = os.getenv('DATABASE_URI', '')
if not uri:
    print('❌ Chưa có DATABASE_URI trong file .env')
    print('   Ví dụ: DATABASE_URI=mysql+mysqlconnector://textqai_user:password@localhost/textqai')
    sys.exit(1)

from app import app, db
import models  # noqa: F401 — đăng ký models với SQLAlchemy

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
        from sqlalchemy import inspect
        existing = set(inspect(db.engine).get_table_names())
    print('\n✅ db.create_all() hoàn tất. Các bảng:')
    for name in TABLES:
        mark = '✓' if name in existing else '?'
        print(f'   {mark} {name}')
    print('\n💡 Gói credit/subscription sẽ được seed tự động khi mở trang Pricing lần đầu.')
    print('   Khởi động app: python app.py')
