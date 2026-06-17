-- TEXTQAI – Khởi tạo database MySQL (legacy / XAMPP)
-- Khuyến nghị dùng PostgreSQL: database/init_postgres.sql
--   mysql -u root -p < database/init_mysql.sql

CREATE DATABASE IF NOT EXISTS textqai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'textqai_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON textqai.* TO 'textqai_user'@'localhost';
FLUSH PRIVILEGES;
