import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.db.session import engine

SQL = """
-- Ensure deployed DB has the same picking index columns as localhost.
ALTER TABLE location_master
ADD COLUMN IF NOT EXISTS pick_index INTEGER DEFAULT 999999;

ALTER TABLE picking_detail
ADD COLUMN IF NOT EXISTS pick_index INTEGER DEFAULT 999999;

-- Helpful indexes for faster picking list generation and print sorting.
CREATE INDEX IF NOT EXISTS ix_location_master_pick_index
ON location_master (pick_index);

CREATE INDEX IF NOT EXISTS ix_location_master_location_id_pick_index
ON location_master (location_id, pick_index);

CREATE INDEX IF NOT EXISTS ix_picking_detail_picking_id_pick_index
ON picking_detail (picking_id, pick_index);

-- Backfill old picking_detail rows using current location_master pick_index.
UPDATE picking_detail pd
SET pick_index = COALESCE(lm.pick_index, 999999)
FROM location_master lm
WHERE pd.location_id = lm.location_id;

UPDATE picking_detail
SET pick_index = 999999
WHERE pick_index IS NULL;
"""

with engine.begin() as conn:
    conn.execute(text(SQL))

print("OK: Sprint 23 Picking Index migration completed")
