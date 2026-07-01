"""Repair GR schema so one PO can have many PA/pallets.

Run:
    python scripts/repair_sprint56_gr_multi_pa.py

Why:
    Some older test schemas may have accidentally created a UNIQUE constraint/index
    on po_no in GR tables. That makes the first PA for a PO work, then the second
    PA fails with a duplicate/unique error. Operational rule is:
        1 PO = N PA
        1 PA = N SKU
        1 PA belongs to only 1 PO
"""

from sqlalchemy import text
from app.db.session import engine

SQL = r"""
-- Keep the correct indexes. These are NON-UNIQUE indexes for lookup speed only.
CREATE INDEX IF NOT EXISTS ix_pallet_header_po_no ON pallet_header(po_no);
CREATE INDEX IF NOT EXISTS ix_pallet_detail_po_no ON pallet_detail(po_no);
CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_no ON inbound_queue(po_no);
CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_pallet ON inbound_queue(po_no, pallet_id);
CREATE INDEX IF NOT EXISTS ix_inbound_queue_po_pallet_sku ON inbound_queue(po_no, pallet_id, sku);

-- Drop known/possible wrong unique constraints created during earlier tests.
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT conrelid::regclass AS table_name, conname
        FROM pg_constraint
        WHERE contype = 'u'
          AND conrelid::regclass::text IN ('pallet_header', 'pallet_detail', 'inbound_queue')
          AND conname IN (
              'uq_pallet_header_po_no',
              'pallet_header_po_no_key',
              'uq_pallet_po',
              'uq_inbound_queue_po_no',
              'inbound_queue_po_no_key',
              'uq_pallet_detail_po_no',
              'pallet_detail_po_no_key'
          )
    LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I', r.table_name, r.conname);
    END LOOP;
END $$;

-- Drop wrong unique indexes on po_no only, if they exist.
DROP INDEX IF EXISTS uq_pallet_header_po_no;
DROP INDEX IF EXISTS ux_pallet_header_po_no;
DROP INDEX IF EXISTS pallet_header_po_no_key;
DROP INDEX IF EXISTS uq_inbound_queue_po_no;
DROP INDEX IF EXISTS ux_inbound_queue_po_no;
DROP INDEX IF EXISTS inbound_queue_po_no_key;
DROP INDEX IF EXISTS uq_pallet_detail_po_no;
DROP INDEX IF EXISTS ux_pallet_detail_po_no;
DROP INDEX IF EXISTS pallet_detail_po_no_key;

-- Re-assert correct uniqueness: pallet_id is unique globally; SKU unique only inside the same PA.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_pallet_sku') THEN
        ALTER TABLE pallet_detail ADD CONSTRAINT uq_pallet_sku UNIQUE (pallet_id, sku);
    END IF;
END $$;
"""

with engine.begin() as conn:
    conn.execute(text(SQL))

print("OK: GR multi-PA repair completed. Rule enabled: 1 PO = N PA, 1 PA = N SKU.")
