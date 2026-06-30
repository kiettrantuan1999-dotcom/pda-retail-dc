from datetime import datetime
import re

from sqlalchemy import text
from app.db.session import engine


def fmt_do_date(value) -> str:
    text_value = str(value or "").strip()
    if not text_value:
        return datetime.now().strftime("%d%m%Y")

    for fmt in (
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(text_value[:19], fmt).strftime("%d%m%Y")
        except Exception:
            pass

    digits = re.sub(r"\D", "", text_value)
    if len(digits) >= 8:
        if digits[:4].isdigit() and 1900 <= int(digits[:4]) <= 2100:
            return digits[6:8] + digits[4:6] + digits[:4]
        return digits[:8]

    return datetime.now().strftime("%d%m%Y")


def suffix(pick_type) -> str:
    return "C" if (pick_type or "").upper() == "CASE" else "L"


with engine.begin() as conn:
    # Bảo đảm cột ngày tạo DO tồn tại trong các DB local cũ.
    conn.execute(text("ALTER TABLE do_detail ADD COLUMN IF NOT EXISTS do_created_date VARCHAR(100) DEFAULT ''"))

    rows = conn.execute(text("""
        SELECT
            h.picking_id,
            h.picking_no,
            h.store_id,
            h.pick_type,
            h.created_at,
            MIN(NULLIF(d.do_created_date, '')) AS do_created_date
        FROM picking_header h
        LEFT JOIN do_detail d
            ON d.store_id = h.store_id
        WHERE h.do_no = 'STORE_PICKING'
        GROUP BY h.picking_id, h.picking_no, h.store_id, h.pick_type, h.created_at
    """)).mappings().all()

    updated = 0
    skipped = 0
    for r in rows:
        store_id = (r["store_id"] or "").strip().upper()
        if not store_id:
            skipped += 1
            continue

        date_source = r["do_created_date"]
        if not date_source and r["created_at"]:
            date_source = r["created_at"].strftime("%d/%m/%Y")

        new_no = f"{fmt_do_date(date_source)}-{store_id}-{suffix(r['pick_type'])}"
        if new_no == (r["picking_no"] or ""):
            skipped += 1
            continue

        conn.execute(
            text("UPDATE picking_header SET picking_no = :new_no WHERE picking_id = :picking_id"),
            {"new_no": new_no, "picking_id": r["picking_id"]},
        )
        updated += 1

print(f"OK sprint40: updated={updated}, skipped={skipped}")
