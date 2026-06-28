import os
import sys
from sqlalchemy import text

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from app.db.session import engine


def column_exists(conn, table_name: str, column_name: str) -> bool:
    sql = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND column_name = :column_name
        LIMIT 1
    """)
    return conn.execute(
        sql,
        {"table_name": table_name, "column_name": column_name}
    ).fetchone() is not None


def add_column_if_missing(conn, table_name: str, column_name: str, column_def: str):
    if column_exists(conn, table_name, column_name):
        print(f"SKIP: {table_name}.{column_name} already exists")
        return

    conn.execute(text(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
    ))
    print(f"OK: added {table_name}.{column_name}")


def main():
    with engine.begin() as conn:
        add_column_if_missing(
            conn,
            "pack_header",
            "staging_status",
            "VARCHAR(50) DEFAULT 'WAIT'"
        )

        add_column_if_missing(
            conn,
            "pack_header",
            "staging_confirm_user",
            "VARCHAR(100)"
        )

        add_column_if_missing(
            conn,
            "pack_header",
            "staging_confirm_time",
            "TIMESTAMP"
        )

        add_column_if_missing(
            conn,
            "pack_header",
            "staging_remark",
            "TEXT"
        )

    print("DONE: Sprint 14 staging migration completed")


if __name__ == "__main__":
    main()