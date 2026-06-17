-- TEXTQAI – Khởi tạo PostgreSQL
-- Chạy với quyền superuser (postgres):
--   psql -U postgres -f database/init_postgres.sql
--
-- Sau đó cấu hình instance/bootstrap.json và chạy: python init_db.py

SELECT 'CREATE DATABASE luanvan_ai ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'luanvan_ai')\gexec

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'textqai_user') THEN
    CREATE ROLE textqai_user WITH LOGIN PASSWORD 'your_password';
  END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE luanvan_ai TO textqai_user;

-- Quyền schema (chạy thêm sau khi đã kết nối vào DB luanvan_ai):
--   psql -U postgres -d luanvan_ai -c "GRANT ALL ON SCHEMA public TO textqai_user;"
--   psql -U postgres -d luanvan_ai -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO textqai_user;"
