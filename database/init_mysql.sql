-- TEXTQAI – Khởi tạo database MySQL / MariaDB
-- Chạy với quyền root:
--   mysql -u root -p < database/init_mysql.sql
--
-- Sau đó tạo bảng: python init_db.py
--   hoặc: mysql -u root -p luanvan_ai < database/schema_mysql.sql

CREATE DATABASE IF NOT EXISTS luanvan_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'textqai_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON luanvan_ai.* TO 'textqai_user'@'localhost';
FLUSH PRIVILEGES;
