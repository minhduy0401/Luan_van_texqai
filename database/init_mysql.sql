-- TEXTQAI – Khởi tạo database MySQL / MariaDB
-- Chạy với quyền root:
--   mysql -u root -p < database/init_mysql.sql
--
-- Sau đó tạo bảng: python init_db.py
--   hoặc: mysql -u root -p luanvan_ai < database/schema_mysql.sql

CREATE DATABASE IF NOT EXISTS textqai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;