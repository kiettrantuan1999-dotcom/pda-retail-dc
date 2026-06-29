from sqlalchemy import text
from app.db.session import engine

SQL = [
    "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS import_key VARCHAR(80)",
    "ALTER TABLE sku_master ADD COLUMN IF NOT EXISTS import_key VARCHAR(80)",
    "ALTER TABLE location_master ADD COLUMN IF NOT EXISTS import_key VARCHAR(80)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_product_master_import_key ON product_master(import_key) WHERE import_key IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_sku_master_import_key ON sku_master(import_key) WHERE import_key IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_location_master_import_key ON location_master(import_key) WHERE import_key IS NOT NULL",
    "UPDATE product_master SET import_key = CONCAT('PROD_', md5(random()::text || sku)) WHERE import_key IS NULL",
    "UPDATE sku_master SET import_key = CONCAT('SKU_', md5(random()::text || sku)) WHERE import_key IS NULL",
    "UPDATE location_master SET import_key = CONCAT('LOC_', md5(random()::text || location_id)) WHERE import_key IS NULL",
]

with engine.begin() as conn:
    for sql in SQL:
        conn.execute(text(sql))

print('OK: Sprint 24 Import Engine v2 migration completed')
