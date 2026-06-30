from sqlalchemy import text
from app.db.session import engine

SQL = """
ALTER TABLE pack_header ADD COLUMN IF NOT EXISTS picked_by TEXT;
ALTER TABLE pack_header ALTER COLUMN do_no TYPE TEXT;
ALTER TABLE pack_log ALTER COLUMN do_no TYPE TEXT;
"""

def main():
    with engine.begin() as conn:
        for stmt in SQL.split(';'):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("OK: migrated pack_header.do_no and pack_log.do_no to TEXT")

if __name__ == "__main__":
    main()
