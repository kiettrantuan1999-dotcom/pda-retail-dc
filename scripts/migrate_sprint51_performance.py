"""Sprint 51 - Performance indexes/schema hardening.

Chạy được trực tiếp từ project root:
    python scripts/migrate_sprint51_performance.py

Mục tiêu:
- Thêm index cho các màn hình scan/danh sách chính.
- Nới các cột do_no/device_name sang TEXT để phù hợp flow store-centric nhiều DO.
- Không làm mất dữ liệu hiện hữu.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402
from app.db.session import engine  # noqa: E402


SQLS = [
    # Schema hardening cho flow store-centric / nhiều DO.
    "ALTER TABLE IF EXISTS pack_header ALTER COLUMN do_no TYPE TEXT",
    "ALTER TABLE IF EXISTS pack_log ALTER COLUMN do_no TYPE TEXT",
    "ALTER TABLE IF EXISTS pack_log ALTER COLUMN device_name TYPE TEXT",

    # Product / SKU master.
    "CREATE INDEX IF NOT EXISTS idx_product_master_barcode ON product_master (barcode)",
    "CREATE INDEX IF NOT EXISTS idx_product_master_sku ON product_master (sku)",
    "CREATE INDEX IF NOT EXISTS idx_sku_master_sku ON sku_master (sku)",
    "CREATE INDEX IF NOT EXISTS idx_sku_master_type ON sku_master (sku_type)",

    # Inbound / Put Away.
    "CREATE INDEX IF NOT EXISTS idx_inbound_queue_status_last_update ON inbound_queue (flow_status, last_update)",
    "CREATE INDEX IF NOT EXISTS idx_inbound_queue_pallet_status ON inbound_queue (pallet_id, flow_status)",
    "CREATE INDEX IF NOT EXISTS idx_inbound_queue_po_pallet ON inbound_queue (po_no, pallet_id)",
    "CREATE INDEX IF NOT EXISTS idx_inbound_queue_barcode ON inbound_queue (barcode)",
    "CREATE INDEX IF NOT EXISTS idx_pallet_detail_pallet_sku_barcode ON pallet_detail (pallet_id, sku, barcode)",
    "CREATE INDEX IF NOT EXISTS idx_pallet_header_status_update ON pallet_header (status, last_update)",
    "CREATE INDEX IF NOT EXISTS idx_location_master_status_pick ON location_master (status, pick_index, location_id)",
    "CREATE INDEX IF NOT EXISTS idx_inventory_balance_sku_location ON inventory_balance (sku, location_id)",
    "CREATE INDEX IF NOT EXISTS idx_inventory_balance_location ON inventory_balance (location_id)",

    # Picking.
    "CREATE INDEX IF NOT EXISTS idx_do_detail_store_status ON do_detail (store_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_do_detail_store_sku ON do_detail (store_id, sku)",
    "CREATE INDEX IF NOT EXISTS idx_do_detail_do_no ON do_detail (do_no)",
    "CREATE INDEX IF NOT EXISTS idx_picking_header_no ON picking_header (picking_no)",
    "CREATE INDEX IF NOT EXISTS idx_picking_header_store_status ON picking_header (store_id, status, pack_status)",
    "CREATE INDEX IF NOT EXISTS idx_picking_header_print_status ON picking_header (print_status, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_picking_detail_picking ON picking_detail (picking_id)",
    "CREATE INDEX IF NOT EXISTS idx_picking_detail_picking_sku ON picking_detail (picking_id, sku)",
    "CREATE INDEX IF NOT EXISTS idx_picking_detail_pack_status ON picking_detail (pack_status)",

    # Pack / staging.
    "CREATE INDEX IF NOT EXISTS idx_pack_header_picking_no ON pack_header (picking_no)",
    "CREATE INDEX IF NOT EXISTS idx_pack_header_status ON pack_header (status)",
    "CREATE INDEX IF NOT EXISTS idx_pack_header_staging_status ON pack_header (staging_status)",
    "CREATE INDEX IF NOT EXISTS idx_pack_log_picking_action ON pack_log (picking_no, action)",
    "CREATE INDEX IF NOT EXISTS idx_pack_log_created ON pack_log (created_at)",

    # Audit/log.
    "CREATE INDEX IF NOT EXISTS idx_audit_log_operation_time ON audit_log (operation, event_time)",
    "CREATE INDEX IF NOT EXISTS idx_operation_log_created ON operation_log (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_error_log_created ON error_log (created_at)",
]

ANALYZE_SQLS = [
    "ANALYZE product_master",
    "ANALYZE sku_master",
    "ANALYZE inbound_queue",
    "ANALYZE inventory_balance",
    "ANALYZE do_detail",
    "ANALYZE picking_header",
    "ANALYZE picking_detail",
    "ANALYZE pack_header",
    "ANALYZE pack_log",
]


def run_sql(conn, sql: str):
    try:
        conn.execute(text(sql))
        print("OK:", sql)
    except Exception as exc:
        # Không dừng toàn bộ migrate nếu local DB thiếu bảng/module chưa dùng.
        print("SKIP:", sql, "=>", exc)


if __name__ == "__main__":
    with engine.begin() as conn:
        for sql in SQLS:
            run_sql(conn, sql)
        for sql in ANALYZE_SQLS:
            run_sql(conn, sql)
    print("DONE Sprint 51 performance migration")
