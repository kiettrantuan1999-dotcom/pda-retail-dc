"""
Sprint 29 - Final fix phiếu in Picking

Fix chính:
1) Đảm bảo DB có đủ cột cho picking_header / picking_detail / do_detail.
2) Backfill barcode theo SKU từ product_master nếu file DO không có barcode.
3) Backfill ĐVT từ file DO upload: cột Excel 'ĐVT' đã được map vào do_detail.uom.
4) Tính lại số tem:
   - Chẵn: CEIL(SL / PCB) từng dòng. Nếu dữ liệu chuẩn chia hết thì đúng bằng SL / PCB.
   - Lẻ: CEIL(SL / PCB) từng SKU line, sau đó tổng phiếu = SUM(label_qty).

Chạy:
    python scripts/migrate_sprint29_picking_print_final.py
"""

from math import ceil
from sqlalchemy import inspect, text

from app.db.session import engine, SessionLocal
from app.models.tables import DoDetail, PickingDetail, ProductMaster, SkuMaster


def _dialect():
    return engine.dialect.name.lower()


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    return column_name in [c["name"] for c in inspector.get_columns(table_name)]


def _add_column(table_name: str, column_name: str, ddl_type: str, default_sql: str | None = None):
    if _has_column(table_name, column_name):
        return False

    dialect = _dialect()
    with engine.begin() as conn:
        if dialect == "postgresql":
            default_part = f" DEFAULT {default_sql}" if default_sql is not None else ""
            conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {ddl_type}{default_part}'))
        else:
            default_part = f" DEFAULT {default_sql}" if default_sql is not None else ""
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}{default_part}"))
    return True


def ensure_schema():
    # picking_header print columns
    _add_column("picking_header", "print_status", "VARCHAR(50)", "'WAIT_PRINT'")
    _add_column("picking_header", "printed_by", "VARCHAR(100)", "''")
    _add_column("picking_header", "printed_at", "TIMESTAMP", None)
    _add_column("picking_header", "print_count", "INTEGER", "0")

    # picking_detail columns used by print screen
    _add_column("picking_detail", "barcode", "VARCHAR(100)", "''")
    _add_column("picking_detail", "uom", "VARCHAR(50)", "''")
    _add_column("picking_detail", "pcb", "INTEGER", "1")
    _add_column("picking_detail", "mhu", "INTEGER", "1")
    _add_column("picking_detail", "label_qty", "INTEGER", "0")
    _add_column("picking_detail", "product_name", "VARCHAR(255)", "''")
    _add_column("picking_detail", "category", "VARCHAR(100)", "''")

    # do_detail uom from uploaded Excel column ĐVT
    _add_column("do_detail", "uom", "VARCHAR(50)", "''")
    _add_column("do_detail", "barcode", "VARCHAR(100)", "''")


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def ceil_div(qty, pcb):
    qty = safe_int(qty, 0)
    pcb = safe_int(pcb, 1)
    if qty <= 0:
        return 0
    if pcb <= 0:
        pcb = 1
    return int(ceil(qty / pcb))


def backfill():
    db = SessionLocal()
    updated = 0
    try:
        details = db.query(PickingDetail).all()
        for d in details:
            sku = (d.sku or "").strip().upper()
            if not sku:
                continue

            changed = False
            product = db.query(ProductMaster).filter(ProductMaster.sku == sku).first()
            sku_master = db.query(SkuMaster).filter(SkuMaster.sku == sku).first()

            do_row = (
                db.query(DoDetail)
                .filter(DoDetail.do_no == d.do_no)
                .filter(DoDetail.store_id == d.store_id)
                .filter(DoDetail.sku == sku)
                .first()
            )

            # Barcode ưu tiên: do_detail nếu có, fallback product_master theo SKU.
            new_barcode = (getattr(do_row, "barcode", "") or "").strip() if do_row else ""
            if not new_barcode and product:
                new_barcode = (product.barcode or "").strip()
            if new_barcode and (d.barcode or "").strip() != new_barcode:
                d.barcode = new_barcode
                changed = True

            # ĐVT ưu tiên từ DO upload: Excel ĐVT -> do_detail.uom.
            new_uom = (getattr(do_row, "uom", "") or "").strip() if do_row else ""
            if not new_uom and product:
                new_uom = (product.uom or "").strip()
            if new_uom and (d.uom or "").strip() != new_uom:
                d.uom = new_uom
                changed = True

            if product:
                if product.product_name and not (d.product_name or "").strip():
                    d.product_name = product.product_name
                    changed = True
                if product.category and not (d.category or "").strip():
                    d.category = product.category
                    changed = True

            if sku_master:
                new_pcb = safe_int(sku_master.pcb, 1)
                new_mhu = safe_int(sku_master.mhu, 1)
                if new_pcb > 0 and safe_int(d.pcb, 0) != new_pcb:
                    d.pcb = new_pcb
                    changed = True
                if new_mhu > 0 and safe_int(d.mhu, 0) != new_mhu:
                    d.mhu = new_mhu
                    changed = True

            new_label = ceil_div(d.qty_pick, d.pcb)
            if safe_int(d.label_qty, 0) != new_label:
                d.label_qty = new_label
                changed = True

            if changed:
                updated += 1

        db.commit()
        return updated
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    ensure_schema()
    updated = backfill()
    print(f"OK: Sprint 29 picking print final migrated. Updated rows: {updated}")


if __name__ == "__main__":
    main()
