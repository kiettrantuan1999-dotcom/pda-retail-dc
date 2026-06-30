"""
Sprint 33 - Fix thiếu cột uom trên picking_detail.

Lỗi xử lý:
(psycopg2.errors.UndefinedColumn) column "uom" of relation "picking_detail" does not exist

Chạy:
python scripts/migrate_sprint33_picking_uom_column.py
"""

from sqlalchemy import text
from app.database import SessionLocal, engine


def column_exists(conn, table_name: str, column_name: str) -> bool:
    sql = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND column_name = :column_name
        LIMIT 1
    """)
    return conn.execute(sql, {"table_name": table_name, "column_name": column_name}).first() is not None


def add_column_if_missing(conn, table_name: str, column_name: str, ddl_type: str, default_sql: str = None):
    if column_exists(conn, table_name, column_name):
        print(f"OK: {table_name}.{column_name} already exists")
        return

    if default_sql is None:
        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}'))
    else:
        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type} DEFAULT {default_sql}'))
    print(f"ADDED: {table_name}.{column_name}")


def main():
    with engine.begin() as conn:
        # Cột gây lỗi chính
        add_column_if_missing(conn, "picking_detail", "uom", "VARCHAR(50)", "''")

        # Các cột print/picking đang dùng, thêm kèm để tránh lỗi dây chuyền
        add_column_if_missing(conn, "picking_detail", "barcode", "VARCHAR(100)", "''")
        add_column_if_missing(conn, "picking_detail", "product_name", "VARCHAR(255)", "''")
        add_column_if_missing(conn, "picking_detail", "category", "VARCHAR(100)", "''")
        add_column_if_missing(conn, "picking_detail", "pcb", "INTEGER", "1")
        add_column_if_missing(conn, "picking_detail", "mhu", "INTEGER", "1")
        add_column_if_missing(conn, "picking_detail", "label_qty", "INTEGER", "0")

        # ĐVT trong file upload được map vào do_detail.uom
        add_column_if_missing(conn, "do_detail", "uom", "VARCHAR(50)", "''")

        # Backfill từ product_master nếu picking_detail còn trống
        conn.execute(text("""
            UPDATE picking_detail pd
            SET
                barcode = COALESCE(NULLIF(pd.barcode, ''), pm.barcode, ''),
                product_name = COALESCE(NULLIF(pd.product_name, ''), pm.product_name, ''),
                category = COALESCE(NULLIF(pd.category, ''), pm.category, ''),
                pcb = COALESCE(NULLIF(pd.pcb, 0), NULLIF(pm.pcb, 0), 1),
                mhu = COALESCE(NULLIF(pd.mhu, 0), NULLIF(pm.pcb, 0), 1),
                uom = COALESCE(NULLIF(pd.uom, ''), pm.uom, '')
            FROM product_master pm
            WHERE pd.sku = pm.sku
        """))

    print("DONE: sprint33 picking uom column migration completed")


if __name__ == "__main__":
    main()
