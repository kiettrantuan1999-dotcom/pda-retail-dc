import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.models.tables import DoDetail, PackHeader, PickingHeader


def main():
    db = SessionLocal()
    now = datetime.utcnow()
    do_no = "DO_STAGING_001"

    try:
        db.query(PackHeader).filter(PackHeader.do_no == do_no).delete()
        db.query(PickingHeader).filter(PickingHeader.do_no == do_no).delete()
        db.query(DoDetail).filter(DoDetail.do_no == do_no).delete()
        db.flush()

        case_pick = PickingHeader(
            picking_no=f"{do_no}-C",
            do_no=do_no,
            store_id="ST001",
            store_name="WIN ĐÀ NẴNG TEST",
            pick_type="CASE",
            status="DONE",
            pack_status="DONE",
            print_status="PRINTED",
            created_at=now - timedelta(hours=2),
            last_update=now,
            packed_by="worker01",
            packed_time=now - timedelta(minutes=20),
            carton_qty=12,
        )
        odd_pick = PickingHeader(
            picking_no=f"{do_no}-L",
            do_no=do_no,
            store_id="ST001",
            store_name="WIN ĐÀ NẴNG TEST",
            pick_type="ODD",
            status="DONE",
            pack_status="DONE",
            print_status="PRINTED",
            created_at=now - timedelta(hours=2),
            last_update=now,
            packed_by="worker02",
            packed_time=now - timedelta(minutes=18),
            carton_qty=8,
        )
        db.add(case_pick)
        db.add(odd_pick)
        db.flush()

        db.add(PackHeader(
            picking_id=case_pick.picking_id,
            picking_no=case_pick.picking_no,
            do_no=do_no,
            store_id="ST001",
            store_name="WIN ĐÀ NẴNG TEST",
            pack_type="CASE",
            sku_line_count=35,
            total_qty=1200,
            actual_package_qty=12,
            status="DONE",
            packed_by="worker01",
            packed_at=now - timedelta(minutes=20),
            staging_status="WAIT",
            created_at=now - timedelta(hours=1),
            last_update=now,
        ))
        db.add(PackHeader(
            picking_id=odd_pick.picking_id,
            picking_no=odd_pick.picking_no,
            do_no=do_no,
            store_id="ST001",
            store_name="WIN ĐÀ NẴNG TEST",
            pack_type="ODD",
            sku_line_count=72,
            total_qty=430,
            actual_package_qty=8,
            status="DONE",
            packed_by="worker02",
            packed_at=now - timedelta(minutes=18),
            staging_status="WAIT",
            created_at=now - timedelta(hours=1),
            last_update=now,
        ))

        for idx in range(1, 6):
            db.add(DoDetail(
                do_no=do_no,
                store_id="ST001",
                store_name="WIN ĐÀ NẴNG TEST",
                sku=f"SKU_STAGE_{idx:03d}",
                barcode=f"8930000000{idx:03d}",
                product_name=f"Sản phẩm test {idx}",
                qty_do=10 * idx,
                qty_packed=10 * idx,
                qty_remain=0,
                status="PACKED",
            ))

        db.commit()
        print("OK: Seed staging test data")
        print(f"DO test: {do_no}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
