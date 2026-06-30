"""
Sprint 31 - Safe Picking Print migration

Chạy từ thư mục gốc project:
    python scripts/migrate_sprint31_picking_print_safe.py

Fix:
- Bổ sung cột thiếu cho picking_header / picking_detail / do_detail nếu DB local chưa có.
- Backfill barcode theo SKU từ product_master.
- Backfill ĐVT từ file DO upload: Excel 'ĐVT' -> do_detail.uom -> picking_detail.uom.
- Backfill PCB từ sku_master.
- Tính lại số tem từng SKU line:
  + Chẵn: SL / PCB, nếu không chia hết thì làm tròn lên để không thiếu tem.
  + Lẻ: CEIL(SL / PCB) từng SKU line, sau đó phiếu cộng tổng.
"""

import os
import sys
from math import ceil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import inspect, text
from app.db.session import engine


def dialect_name():
    return engine.dialect.name.lower()


def table_columns(table_name: str) -> set[str]:
    try:
        return {c["name"] for c in inspect(engine).get_columns(table_name)}
    except Exception:
        return set()


def add_column(table_name: str, column_name: str, ddl_type: str, default_sql: str | None = None):
    cols = table_columns(table_name)
    if column_name in cols:
        return False

    default_part = f" DEFAULT {default_sql}" if default_sql is not None else ""
    with engine.begin() as conn:
        if dialect_name() == "postgresql":
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {ddl_type}{default_part}"))
        else:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}{default_part}"))
    print(f"ADD COLUMN: {table_name}.{column_name}")
    return True


def ensure_schema():
    add_column("picking_header", "print_status", "VARCHAR(50)", "'WAIT_PRINT'")
    add_column("picking_header", "printed_by", "VARCHAR(100)", "''")
    add_column("picking_header", "printed_at", "TIMESTAMP", None)
    add_column("picking_header", "print_count", "INTEGER", "0")

    add_column("picking_detail", "barcode", "VARCHAR(100)", "''")
    add_column("picking_detail", "uom", "VARCHAR(50)", "''")
    add_column("picking_detail", "pcb", "INTEGER", "1")
    add_column("picking_detail", "mhu", "INTEGER", "1")
    add_column("picking_detail", "label_qty", "INTEGER", "0")
    add_column("picking_detail", "product_name", "VARCHAR(255)", "''")
    add_column("picking_detail", "category", "VARCHAR(100)", "''")

    add_column("do_detail", "barcode", "VARCHAR(100)", "''")
    add_column("do_detail", "uom", "VARCHAR(50)", "''")


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def label_qty(qty, pcb):
    qty_i = max(safe_int(qty, 0), 0)
    pcb_i = max(safe_int(pcb, 1), 1)
    if qty_i <= 0:
        return 0
    return int(ceil(qty_i / pcb_i))


def backfill():
    with engine.begin() as conn:
        # Barcode, tên hàng, ĐVT: ưu tiên DO upload.
        conn.execute(text("""
            UPDATE picking_detail AS pd
            SET
                barcode = COALESCE(NULLIF(pd.barcode, ''), NULLIF(dd.barcode, ''), ''),
                uom = COALESCE(NULLIF(pd.uom, ''), NULLIF(dd.uom, ''), ''),
                product_name = COALESCE(NULLIF(pd.product_name, ''), NULLIF(dd.product_name, ''), '')
            FROM do_detail AS dd
            WHERE dd.do_no = pd.do_no
              AND dd.store_id = pd.store_id
              AND UPPER(TRIM(dd.sku)) = UPPER(TRIM(pd.sku))
        """))

        # Fallback product_master cho những dòng không match do_detail.
        conn.execute(text("""
            UPDATE picking_detail AS pd
            SET
                barcode = COALESCE(NULLIF(pd.barcode, ''), NULLIF(pm.barcode, ''), ''),
                uom = COALESCE(NULLIF(pd.uom, ''), NULLIF(pm.uom, ''), ''),
                product_name = COALESCE(NULLIF(pd.product_name, ''), NULLIF(pm.product_name, ''), ''),
                category = COALESCE(NULLIF(pd.category, ''), NULLIF(pm.category, ''), 'CHƯA PHÂN NGÀNH')
            FROM product_master AS pm
            WHERE UPPER(TRIM(pm.sku)) = UPPER(TRIM(pd.sku))
        """))

        conn.execute(text("""
            UPDATE picking_detail AS pd
            SET
                pcb = COALESCE(NULLIF(pd.pcb, 0), NULLIF(sm.pcb, 0), 1),
                mhu = COALESCE(NULLIF(pd.mhu, 0), NULLIF(sm.mhu, 0), 1)
            FROM sku_master AS sm
            WHERE UPPER(TRIM(sm.sku)) = UPPER(TRIM(pd.sku))
        """))

    # Tính label_qty bằng Python để tương thích SQLite/PostgreSQL.
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT picking_detail_id, qty_pick, pcb FROM picking_detail")).fetchall()
        for r in rows:
            m = r._mapping
            conn.execute(
                text("UPDATE picking_detail SET label_qty = :label_qty WHERE picking_detail_id = :id"),
                {"label_qty": label_qty(m.get("qty_pick"), m.get("pcb")), "id": m.get("picking_detail_id")},
            )
    return len(rows)


def main():
    ensure_schema()
    rows = backfill()
    print(f"OK: Sprint 31 migrated. Backfilled picking_detail rows: {rows}")


if __name__ == "__main__":
    main()
