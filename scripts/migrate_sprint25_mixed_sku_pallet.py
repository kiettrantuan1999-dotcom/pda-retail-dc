from sqlalchemy import text
from app.db.session import engine

SQL = """
CREATE TABLE IF NOT EXISTS pallet_header (
    pallet_id VARCHAR(100) PRIMARY KEY,
    po_no VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_by VARCHAR(100) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pallet_header_po_no ON pallet_header(po_no);
CREATE INDEX IF NOT EXISTS ix_pallet_header_status ON pallet_header(status);

CREATE TABLE IF NOT EXISTS pallet_detail (
    pallet_detail_id SERIAL PRIMARY KEY,
    pallet_id VARCHAR(100) NOT NULL,
    po_no VARCHAR(100) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    barcode VARCHAR(100) NOT NULL,
    qty_gr INTEGER DEFAULT 0,
    qty_putaway INTEGER DEFAULT 0,
    qty_remain_putaway INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pallet_detail_pallet_id ON pallet_detail(pallet_id);
CREATE INDEX IF NOT EXISTS ix_pallet_detail_po_no ON pallet_detail(po_no);
CREATE INDEX IF NOT EXISTS ix_pallet_detail_sku ON pallet_detail(sku);
CREATE INDEX IF NOT EXISTS ix_pallet_detail_barcode ON pallet_detail(barcode);
CREATE INDEX IF NOT EXISTS ix_pallet_detail_status ON pallet_detail(status);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_pallet_sku'
    ) THEN
        ALTER TABLE pallet_detail ADD CONSTRAINT uq_pallet_sku UNIQUE (pallet_id, sku);
    END IF;
END $$;
"""

with engine.begin() as conn:
    conn.execute(text(SQL))

print("OK: Sprint 25 mixed SKU pallet migration completed")
