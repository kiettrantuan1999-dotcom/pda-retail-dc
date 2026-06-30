from sqlalchemy import text
from app.db.session import engine

SQL = """
ALTER TABLE pack_header ALTER COLUMN do_no TYPE TEXT;
ALTER TABLE pack_log ALTER COLUMN do_no TYPE TEXT;
ALTER TABLE pack_log ALTER COLUMN device_name TYPE TEXT;
"""

if __name__ == "__main__":
    with engine.begin() as conn:
        for stmt in SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("OK: Sprint 45 pack pending/schema migration completed")
