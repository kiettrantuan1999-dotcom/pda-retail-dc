import os
import sys

from sqlalchemy import text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db.session import engine


INDEX_SQL = [
    # GR nhập hàng / confirm PA / history
    "CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_pallet ON inbound_queue (po_no, pallet_id)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_sku ON inbound_queue (po_no, sku)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_pallet_sku ON inbound_queue (po_no, pallet_id, sku)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_queue_status ON inbound_queue (flow_status)",

    # Đối chiếu PO detail
    "CREATE INDEX IF NOT EXISTS ix_po_detail_po_sku ON po_detail (po_no, sku)",

    # PA header
    "CREATE INDEX IF NOT EXISTS ix_pallet_header_pallet_po ON pallet_header (pallet_id, po_no)",
    "CREATE INDEX IF NOT EXISTS ix_pallet_detail_pallet_sku ON pallet_detail (pallet_id, sku)",

    # Master lookup khi scan barcode/SKU
    "CREATE INDEX IF NOT EXISTS ix_product_master_sku ON product_master (sku)",
    "CREATE INDEX IF NOT EXISTS ix_product_master_barcode ON product_master (barcode)",
    "CREATE INDEX IF NOT EXISTS ix_product_barcode_alias_barcode ON product_barcode_alias (barcode)",
    "CREATE INDEX IF NOT EXISTS ix_product_barcode_alias_sku ON product_barcode_alias (sku)",
    "CREATE INDEX IF NOT EXISTS ix_sku_master_sku ON sku_master (sku)",
]


def main():
    with engine.begin() as conn:
        for sql in INDEX_SQL:
            conn.execute(text(sql))
    print("OK: performance indexes created/verified")


if __name__ == "__main__":
    main()
