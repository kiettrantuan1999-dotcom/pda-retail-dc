"""
Sprint 26 - Rebuild picking slips by store.

Dùng khi trước đó hệ thống đã tạo phiếu theo DO và cần tạo lại theo cửa hàng.
Lệnh chạy từ thư mục gốc project:
    python scripts/migrate_sprint26_store_picking.py
hoặc:
    python -m scripts.migrate_sprint26_store_picking
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.db.session import SessionLocal
from app.models.tables import DoDetail, PickingDetail, PickingHeader
from app.services.picking_service import tao_phieu_lay_hang_theo_cua_hang


def main():
    db = SessionLocal()
    try:
        locked = (
            db.query(PickingHeader)
            .filter(PickingHeader.pack_status == "DONE")
            .count()
        )
        if locked:
            print(f"STOP: Đang có {locked} phiếu đã pack. Không tự rebuild để tránh mất trace.")
            print("Nếu đây là dữ liệu test, hãy xóa dữ liệu test hoặc reset bảng trước rồi chạy lại.")
            return

        detail_deleted = db.query(PickingDetail).delete()
        header_deleted = db.query(PickingHeader).delete()
        db.commit()

        store_ids = [x[0] for x in db.query(DoDetail.store_id).distinct().all() if x[0]]
        created = 0
        for store_id in store_ids:
            result = tao_phieu_lay_hang_theo_cua_hang(db, store_id)
            created += int(result.get("so_phieu_lay_hang") or 0)

        print("OK: rebuilt picking slips by store")
        print(f"Deleted headers: {header_deleted}")
        print(f"Deleted details: {detail_deleted}")
        print(f"Stores: {len(store_ids)}")
        print(f"Picking slips created: {created}")
    except Exception as exc:
        db.rollback()
        print("ERROR:", exc)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
