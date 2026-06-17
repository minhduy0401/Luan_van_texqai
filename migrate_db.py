#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_db.py – Migration schema một lần (legacy MySQL / XAMPP).

PostgreSQL mới: chỉ cần python init_db.py (db.create_all()).

MySQL legacy — chạy một lần:
    python migrate_db.py
"""
import os
import sys

from utils.bootstrap_config import get_database_uri

DB_URI = get_database_uri()

if not DB_URI.startswith('mysql'):
    print('ℹ️  migrate_db.py chỉ dùng cho MySQL legacy.')
    print('   PostgreSQL: cấu hình bootstrap.json rồi chạy python init_db.py')
    sys.exit(0)

try:
    import mysql.connector
except ImportError:
    print('❌ Cần mysql-connector-python: pip install mysql-connector-python')
    sys.exit(1)

# Parse basic URI: mysql+mysqlconnector://user:pass@host/dbname
# Format: mysql+mysqlconnector://user:password@host:port/dbname
import re
m = re.match(r'mysql\+mysqlconnector://([^:@]*)(?::([^@]*))?@([^:/]+)(?::(\d+))?/(\w+)', DB_URI)
if not m:
    print("❌ Không parse được DATABASE_URI")
    sys.exit(1)

db_user     = m.group(1)
db_password = m.group(2) or ''
db_host     = m.group(3)
db_port     = int(m.group(4) or 3306)
db_name     = m.group(5)

print(f"🔗 Connecting to {db_host}:{db_port}/{db_name} as {db_user}")

conn = mysql.connector.connect(
    host=db_host, port=db_port,
    user=db_user, password=db_password,
    database=db_name,
)
cursor = conn.cursor()

def col_exists(table, col):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name=%s AND column_name=%s",
        (db_name, table, col)
    )
    return cursor.fetchone()[0] > 0

def table_exists(table):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema=%s AND table_name=%s",
        (db_name, table)
    )
    return cursor.fetchone()[0] > 0

print("\n📋 Step 1: Update `users` table schema")

# Make username nullable
cursor.execute("ALTER TABLE users MODIFY COLUMN username VARCHAR(100) NULL")
print("  ✅ username → nullable")

# Add email
if not col_exists('users', 'email'):
    cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE NULL AFTER username")
    print("  ✅ Added column: email")
else:
    print("  ℹ️  email already exists")

# Add display_name
if not col_exists('users', 'display_name'):
    cursor.execute("ALTER TABLE users ADD COLUMN display_name VARCHAR(255) NULL AFTER email")
    print("  ✅ Added column: display_name")
else:
    print("  ℹ️  display_name already exists")

# Add is_active
if not col_exists('users', 'is_active'):
    cursor.execute("ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER display_name")
    print("  ✅ Added column: is_active")
else:
    print("  ℹ️  is_active already exists")

# Add created_at
if not col_exists('users', 'created_at'):
    cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT NOW() AFTER is_active")
    print("  ✅ Added column: created_at")
else:
    print("  ℹ️  created_at already exists")

conn.commit()

print("\n📋 Step 2: Create `user_auth_providers` table")

if not table_exists('user_auth_providers'):
    cursor.execute("""
        CREATE TABLE user_auth_providers (
            id                INT AUTO_INCREMENT PRIMARY KEY,
            user_id           INT NOT NULL,
            provider          VARCHAR(50) NOT NULL,
            provider_user_id  VARCHAR(255) NULL,
            provider_email    VARCHAR(255) NULL,
            password_hash     VARCHAR(255) NULL,
            created_at        DATETIME DEFAULT NOW(),
            CONSTRAINT fk_auth_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT uq_provider_user UNIQUE (provider, provider_user_id)
        )
    """)
    print("  ✅ Created table: user_auth_providers")
else:
    print("  ℹ️  user_auth_providers already exists")

conn.commit()

print("\n📋 Step 3: Migrate existing user passwords → user_auth_providers")

# Only do this if `password` column still exists in users
if col_exists('users', 'password'):
    cursor.execute("SELECT id, username, password FROM users")
    existing_users = cursor.fetchall()
    migrated = 0
    for uid, uname, pw_hash in existing_users:
        # Check if local provider already exists for this user
        cursor.execute(
            "SELECT COUNT(*) FROM user_auth_providers WHERE user_id=%s AND provider='local'",
            (uid,)
        )
        if cursor.fetchone()[0] == 0 and pw_hash:
            cursor.execute(
                "INSERT INTO user_auth_providers (user_id, provider, password_hash) VALUES (%s, 'local', %s)",
                (uid, pw_hash)
            )
            migrated += 1
    conn.commit()
    print(f"  ✅ Migrated {migrated} user(s) to user_auth_providers")

    # Set display_name from username for existing users
    cursor.execute("UPDATE users SET display_name = username WHERE display_name IS NULL AND username IS NOT NULL")
    conn.commit()
    print("  ✅ Set display_name from username for existing users")

    # Drop old password column
    cursor.execute("ALTER TABLE users DROP COLUMN password")
    conn.commit()
    print("  ✅ Dropped old `password` column from users")
else:
    print("  ℹ️  `password` column already removed, skipping migration")

print("\n📋 Step 4: Add batch_id to qa_results")
if not col_exists('qa_results', 'batch_id'):
    cursor.execute("ALTER TABLE qa_results ADD COLUMN batch_id VARCHAR(20) NULL AFTER points_breakdown")
    conn.commit()
    print("  ✅ Added column: batch_id")
else:
    print("  ℹ️  batch_id already exists")

cursor.close()
conn.close()

print("\n🎉 Migration complete! You can now start the app.")
