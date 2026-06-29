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

print("OK: Sprint 22 Put Away master migration completed")
