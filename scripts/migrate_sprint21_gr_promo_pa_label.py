from sqlalchemy import text
from app.db.session import engine

SQL = """
ALTER TABLE inbound_queue
ADD COLUMN IF NOT EXISTS qty_promo INTEGER DEFAULT 0;

ALTER TABLE gr_log
ADD COLUMN IF NOT EXISTS qty_promo INTEGER DEFAULT 0;

ALTER TABLE pallet_detail
ADD COLUMN IF NOT EXISTS qty_promo INTEGER DEFAULT 0;
"""

with engine.begin() as conn:
    conn.execute(text(SQL))

print("OK: Sprint 21 migrated qty_promo for GR / inbound_queue / pallet_detail")
