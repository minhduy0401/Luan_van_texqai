-- TEXTQAI – Khởi tạo database MySQL
-- Chạy với quyền root (hoặc user có quyền CREATE DATABASE):
--   mysql -u root -p < database/init.sql

CREATE DATABASE IF NOT EXISTS textqai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'textqai_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON textqai.* TO 'textqai_user'@'localhost';
FLUSH PRIVILEGES;

-- Sau bước này, cấu hình .env rồi chạy: python init_db.py
-- (hoặc python app.py — app cũng tự gọi db.create_all() lần đầu)
