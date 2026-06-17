# utils/db_schema.py – Migration schema nhẹ, không phụ thuộc dialect cụ thể
from sqlalchemy import inspect, text


def ensure_column(engine, table: str, column: str, ddl: str) -> bool:
    """Thêm cột nếu chưa có. ddl = phần sau ADD COLUMN, VD: 'terms_agreed_at TIMESTAMP NULL'."""
    insp = inspect(engine)
    if column in {c['name'] for c in insp.get_columns(table)}:
        return False
    with engine.begin() as conn:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {ddl}'))
    return True
