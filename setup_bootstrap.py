#!/usr/bin/env python3
"""Tạo instance/bootstrap.json từ bootstrap.json.example (lần cài đặt đầu tiên)."""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(ROOT, 'bootstrap.json.example')
TARGET_DIR = os.path.join(ROOT, 'instance')
TARGET = os.path.join(TARGET_DIR, 'bootstrap.json')


def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    if os.path.isfile(TARGET):
        print(f'ℹ️  Đã tồn tại: {TARGET}')
        print('   Sửa database_uri trực tiếp trong file đó nếu cần.')
        return
    if not os.path.isfile(EXAMPLE):
        print(f'❌ Không tìm thấy {EXAMPLE}')
        return
    shutil.copy(EXAMPLE, TARGET)
    print(f'✅ Đã tạo {TARGET}')
    print('   Sửa database_uri và secret_key, rồi chạy: python init_db.py')


if __name__ == '__main__':
    main()
