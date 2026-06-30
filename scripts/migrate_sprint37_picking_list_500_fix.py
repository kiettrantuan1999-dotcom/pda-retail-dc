"""
Sprint 36 - Bổ sung thông tin điều phối cho Picking List:
- do_detail.trip_no
- picking_header.wave
- picking_header.khung_gio
- picking_header.loai_giao
- picking_header.trip_no

Chạy:
    python scripts/migrate_sprint36_picking_wave_delivery.py
"""
from sqlalchemy import text

from app.db.session import engine


def add_column_if_missing(conn, table_name: str, column_name: str, ddl_type: str = "VARCHAR(100)"):
    exists = conn.execute(text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND column_name = :column_name
    """), {"table_name": table_name, "column_name": column_name}).first()
    if not exists:
        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type} DEFAULT \'\''))
        print(f"OK added {table_name}.{column_name}")
    else:
        print(f"SKIP exists {table_name}.{column_name}")


def main():
    with engine.begin() as conn:
        add_column_if_missing(conn, "do_detail", "trip_no")
        for col in ["wave", "khung_gio", "loai_giao", "trip_no"]:
            add_column_if_missing(conn, "picking_header", col)

        # Backfill header metadata từ do_detail cho các phiếu store picking hiện hữu.
        conn.execute(text("""
            UPDATE picking_header h
            SET
                wave = COALESCE(NULLIF(h.wave, ''), x.wave, ''),
                khung_gio = COALESCE(NULLIF(h.khung_gio, ''), x.khung_gio, ''),
                loai_giao = COALESCE(NULLIF(h.loai_giao, ''), x.loai_giao, ''),
                trip_no = COALESCE(NULLIF(h.trip_no, ''), x.trip_no, '')
            FROM (
                SELECT
                    store_id,
                    STRING_AGG(DISTINCT NULLIF(wave, ''), ', ') AS wave,
                    STRING_AGG(DISTINCT NULLIF(khung_gio, ''), ', ') AS khung_gio,
                    STRING_AGG(DISTINCT NULLIF(loai_giao, ''), ', ') AS loai_giao,
                    STRING_AGG(DISTINCT NULLIF(trip_no, ''), ', ') AS trip_no
                FROM do_detail
                GROUP BY store_id
            ) x
            WHERE h.store_id = x.store_id
              AND h.do_no = 'STORE_PICKING'
        """))

    print("DONE Sprint 36 migration")


if __name__ == "__main__":
    main()
