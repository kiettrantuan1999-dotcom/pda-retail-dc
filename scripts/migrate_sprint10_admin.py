import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text

from app.db.session import engine


TABLE_NAME = "app_user"

# DDL dùng được cho SQLite local và PostgreSQL Railway ở mức cơ bản.
COLUMNS = {
    "full_name": "VARCHAR(255) DEFAULT ''",
    "email": "VARCHAR(255) DEFAULT ''",
    "phone": "VARCHAR(50) DEFAULT ''",
    "last_login": "TIMESTAMP NULL",
    "created_by": "VARCHAR(100) DEFAULT ''",
    "updated_at": "TIMESTAMP NULL",
}


def main():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if TABLE_NAME not in table_names:
        print("Chưa có bảng app_user. Chạy python create_tables.py trước.")
        return

    existing = {c["name"] for c in inspector.get_columns(TABLE_NAME)}

    with engine.begin() as conn:
        for col, ddl in COLUMNS.items():
            if col in existing:
                print(f"SKIP: {col} đã tồn tại")
                continue
            conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col} {ddl}"))
            print(f"OK: added {col}")

    print("OK: Sprint 10 admin migration completed")


if __name__ == "__main__":
    main()
