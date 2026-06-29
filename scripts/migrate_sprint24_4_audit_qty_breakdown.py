from sqlalchemy import text
from app.db.session import engine

SQL = """
ALTER TABLE audit_log
ADD COLUMN IF NOT EXISTS qty_regular INTEGER DEFAULT 0;

ALTER TABLE audit_log
ADD COLUMN IF NOT EXISTS qty_promo INTEGER DEFAULT 0;

ALTER TABLE audit_log
ADD COLUMN IF NOT EXISTS qty_total INTEGER DEFAULT 0;

UPDATE audit_log
SET qty_total = COALESCE(NULLIF(qty_total, 0), qty_after, 0)
WHERE qty_total IS NULL OR qty_total = 0;
"""

with engine.begin() as conn:
    conn.execute(text(SQL))

print("OK: Sprint 24.4 audit qty breakdown migrated")
