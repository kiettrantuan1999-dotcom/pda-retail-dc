import sys
from pathlib import Path

# Thêm project root vào PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.db.session import engine


SQL_LIST = [

    """
    ALTER TABLE picking_header
    ADD COLUMN pack_status VARCHAR(50) DEFAULT 'WAIT';
    """,

    """
    CREATE TABLE IF NOT EXISTS pack_log (

        pack_log_id INTEGER PRIMARY KEY AUTOINCREMENT,

        picking_no VARCHAR(120),

        do_no VARCHAR(100),

        store_id VARCHAR(100),

        pack_type VARCHAR(50),

        sku_line_count INTEGER DEFAULT 0,

        total_qty INTEGER DEFAULT 0,

        actual_package_qty INTEGER DEFAULT 0,

        action VARCHAR(100),

        user_name VARCHAR(100),

        device_name TEXT,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP

    );
    """

]


def main():

    with engine.begin() as conn:

        for sql in SQL_LIST:

            try:
                conn.execute(text(sql))
                print("OK")

            except Exception as e:
                print(e)

    print("===== Sprint 4 migration completed =====")


if __name__ == "__main__":
    main()