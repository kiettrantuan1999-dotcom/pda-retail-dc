import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.db.session import engine

SQL = """
ALTER TABLE category_aisle_master
ADD COLUMN IF NOT EXISTS putaway_type VARCHAR(20) DEFAULT '';

ALTER TABLE category_aisle_master
ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE;

ALTER TABLE location_master
ADD COLUMN IF NOT EXISTS aisle VARCHAR(30) DEFAULT '';

ALTER TABLE location_master
ADD COLUMN IF NOT EXISTS bay VARCHAR(30) DEFAULT '';

ALTER TABLE location_master
ADD COLUMN IF NOT EXISTS level VARCHAR(30) DEFAULT '';

ALTER TABLE location_master
ADD COLUMN IF NOT EXISTS putaway_index INTEGER DEFAULT 999999;

ALTER TABLE location_master
ADD COLUMN IF NOT EXISTS travel_sequence INTEGER DEFAULT 999999;

UPDATE location_master
SET aisle = COALESCE(NULLIF(aisle, ''), split_part(location_id, '-', 1));

UPDATE location_master
SET putaway_index = COALESCE(NULLIF(putaway_index, 999999), pick_index, 999999),
    travel_sequence = COALESCE(NULLIF(travel_sequence, 999999), pick_index, 999999);

CREATE INDEX IF NOT EXISTS ix_location_master_aisle ON location_master (aisle);
CREATE INDEX IF NOT EXISTS ix_location_master_status ON location_master (status);
CREATE INDEX IF NOT EXISTS ix_location_master_pick_index ON location_master (pick_index);
CREATE INDEX IF NOT EXISTS ix_location_master_putaway_index ON location_master (putaway_index);
CREATE INDEX IF NOT EXISTS ix_location_master_travel_sequence ON location_master (travel_sequence);

CREATE TABLE IF NOT EXISTS sku_location_override (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) NOT NULL,
    barcode VARCHAR(100) DEFAULT '',
    product_name VARCHAR(255) DEFAULT '',
    putaway_type VARCHAR(20) DEFAULT '',
    aisle VARCHAR(20) NOT NULL,
    priority INTEGER DEFAULT 1,
    reason TEXT DEFAULT '',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sku_location_override UNIQUE (sku, aisle)
);

CREATE INDEX IF NOT EXISTS ix_sku_location_override_sku ON sku_location_override (sku);
CREATE INDEX IF NOT EXISTS ix_sku_location_override_barcode ON sku_location_override (barcode);
CREATE INDEX IF NOT EXISTS ix_sku_location_override_aisle ON sku_location_override (aisle);
CREATE INDEX IF NOT EXISTS ix_sku_location_override_active ON sku_location_override (active);
CREATE INDEX IF NOT EXISTS ix_sku_location_override_putaway_type ON sku_location_override (putaway_type);
"""

with engine.begin() as conn:
    conn.execute(text(SQL))

print("OK: Sprint 22 Put Away + Master Rule + Location Index migration completed")
