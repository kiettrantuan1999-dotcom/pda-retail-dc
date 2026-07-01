"""Sprint 52 - GR PO reconcile + import/scan performance indexes.

Run:
    python scripts/migrate_sprint52_gr_po_reconcile_perf.py
    hoặc: python -m scripts.migrate_sprint52_gr_po_reconcile_perf
"""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from app.db.session import engine

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS ix_po_detail_po_barcode ON po_detail (po_no, barcode)",
    "CREATE INDEX IF NOT EXISTS ix_po_detail_po_sku_barcode ON po_detail (po_no, sku, barcode)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_sku_barcode ON inbound_queue (po_no, sku, barcode)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_pallet ON inbound_queue (po_no, pallet_id)",
    "CREATE INDEX IF NOT EXISTS ix_pallet_detail_po_pallet ON pallet_detail (po_no, pallet_id)",
]


def main():
    with engine.begin() as conn:
        for sql in INDEX_SQL:
            conn.execute(text(sql))
    print("OK: Sprint 52 indexes created/verified")


if __name__ == "__main__":
    main()
