from app.db.session import engine

DDL = """
CREATE TABLE IF NOT EXISTS product_barcode_alias (
    barcode VARCHAR(100) PRIMARY KEY,
    sku VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) DEFAULT '',
    uom VARCHAR(50) DEFAULT 'EA',
    category VARCHAR(100) DEFAULT '',
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_product_barcode_alias_sku ON product_barcode_alias (sku);
CREATE INDEX IF NOT EXISTS ix_product_barcode_alias_is_primary ON product_barcode_alias (is_primary);

INSERT INTO product_barcode_alias (barcode, sku, product_name, uom, category, is_primary, created_at, last_update)
SELECT barcode, sku, product_name, uom, category, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM product_master
WHERE barcode IS NOT NULL AND TRIM(barcode) <> ''
ON CONFLICT (barcode) DO UPDATE SET
    sku = EXCLUDED.sku,
    product_name = EXCLUDED.product_name,
    uom = EXCLUDED.uom,
    category = EXCLUDED.category,
    is_primary = TRUE,
    last_update = CURRENT_TIMESTAMP;
"""


def main():
    with engine.begin() as conn:
        conn.exec_driver_sql(DDL)
    print("OK: created/synced product_barcode_alias")


if __name__ == "__main__":
    main()
