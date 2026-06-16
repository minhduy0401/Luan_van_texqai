#!/usr/bin/env python3
"""Tạo tài khoản admin hoặc nâng quyền admin cho user có sẵn.

Chạy sau khi đã cấu hình instance/bootstrap.json và tạo bảng (python init_db.py).

Usage:
    python create_admin.py
    python create_admin.py --username admin --email admin@example.com
    python create_admin.py --username admin --promote
"""
import argparse
import getpass
import sys
from datetime import datetime

from werkzeug.security import generate_password_hash

from app import app, db
from models import User, UserAuthProvider


def _create_admin(username: str, email: str, password: str) -> None:
    user = User(
        username=username,
        email=email or None,
        display_name=username,
        is_admin=True,
        credits=999,
        terms_agreed_at=datetime.utcnow(),
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(UserAuthProvider(
        user_id=user.id,
        provider='local',
        password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
    ))
    db.session.commit()
    print(f'✅ Đã tạo tài khoản admin: {username}')
    if email:
        print(f'   Email: {email}')


def _promote_admin(username: str, email: str) -> bool:
    user = User.query.filter_by(username=username).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()
    if not user:
        return False
    if not user.is_admin:
        user.is_admin = True
        db.session.commit()
        print(f'✅ Đã nâng quyền admin cho: {user.username or user.email}')
    else:
        print(f'ℹ️  {user.username or user.email} đã là admin.')
    return True


def main():
    parser = argparse.ArgumentParser(description='Tạo hoặc nâng quyền tài khoản admin TEXTQAI')
    parser.add_argument('--username', help='Tên đăng nhập admin')
    parser.add_argument('--email', default='', help='Email (tùy chọn)')
    parser.add_argument('--password', help='Mật khẩu (bỏ trống sẽ hỏi ẩn)')
    parser.add_argument('--promote', action='store_true',
                        help='Chỉ nâng quyền admin cho user đã tồn tại (đã đăng ký qua web)')
    args = parser.parse_args()

    username = (args.username or input('Tên đăng nhập admin: ')).strip()
    if not username:
        print('❌ Tên đăng nhập không được để trống.')
        sys.exit(1)

    email = (args.email or input('Email (Enter để bỏ qua): ')).strip()

    with app.app_context():
        if args.promote:
            if not _promote_admin(username, email):
                print('❌ Không tìm thấy user. Đăng ký qua /register trước, hoặc bỏ --promote để tạo mới.')
                sys.exit(1)
            return

        if User.query.filter_by(username=username).first():
            print(f'❌ Username "{username}" đã tồn tại. Dùng --promote để nâng quyền admin.')
            sys.exit(1)
        if email and User.query.filter_by(email=email).first():
            print(f'❌ Email "{email}" đã được dùng.')
            sys.exit(1)

        password = args.password or getpass.getpass('Mật khẩu admin: ')
        confirm = getpass.getpass('Nhập lại mật khẩu: ')
        if password != confirm:
            print('❌ Mật khẩu không khớp.')
            sys.exit(1)
        if len(password) < 6:
            print('❌ Mật khẩu tối thiểu 6 ký tự.')
            sys.exit(1)

        _create_admin(username, email, password)
        print('   Đăng nhập tại /login → menu Admin xuất hiện sau khi đăng nhập.')


if __name__ == '__main__':
    main()
