"""Repair Sprint 54 - đồng bộ GR -> Put Away.

Mục tiêu:
- 1 dòng pallet_detail (PA + SKU) phải có 1 dòng inbound_queue.
- qty_remain_putaway = qty_gr - qty_putaway.
- flow_status của queue chờ cất dựa theo lượng còn cất, không dựa vào thiếu/đủ PO.
- po_detail.qty_received tính lại theo tổng qty_gr thực tế trong inbound_queue theo PO + SKU.

Chạy từ thư mục gốc project:
    python -m scripts.repair_sprint54_putaway_gr_sync
"""
from datetime import datetime
from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.tables import InboundQueue, PalletDetail, PoDetail


DONE_STATUSES = {"DONE"}
COMPLETED_PA_STATUSES = {"WAIT_PUTAWAY", "PARTIAL", "DONE"}


def norm(value: str) -> str:
    return str(value or "").strip()


def upper(value: str) -> str:
    return norm(value).upper()


def receipt_status(qty_total: int, qty_order: int) -> str:
    qty_total = int(qty_total or 0)
    qty_order = int(qty_order or 0)
    if qty_total > qty_order:
        return "DƯ"
    if qty_total == qty_order and qty_order > 0:
        return "ĐỦ"
    return "THIẾU"


def main() -> None:
    db = SessionLocal()
    now = datetime.utcnow()
    created_queue = 0
    synced_queue = 0
    synced_po = 0

    try:
        details = db.query(PalletDetail).all()

        for d in details:
            po_no = norm(d.po_no)
            pallet_id = upper(d.pallet_id)
            sku = upper(d.sku)
            if not po_no or not pallet_id or not sku:
                continue

            q = (
                db.query(InboundQueue)
                .filter(
                    func.upper(func.trim(InboundQueue.po_no)) == po_no.upper(),
                    func.upper(func.trim(InboundQueue.pallet_id)) == pallet_id,
                    func.upper(func.trim(InboundQueue.sku)) == sku,
                )
                .first()
            )

            qty_gr = int(d.qty_gr or 0)
            qty_putaway = int(d.qty_putaway or 0)
            remain = max(qty_gr - qty_putaway, 0)
            detail_status = upper(d.status)

            if remain <= 0:
                flow_status = "DONE"
            elif qty_putaway > 0:
                flow_status = "PARTIAL"
            elif detail_status in COMPLETED_PA_STATUSES:
                flow_status = "WAIT_PUTAWAY"
            else:
                flow_status = "DRAFT"

            if q:
                q.qty_gr = qty_gr
                q.qty_putaway = qty_putaway
                q.qty_remain_putaway = remain
                q.flow_status = flow_status
                q.last_update = now
                synced_queue += 1
            else:
                db.add(InboundQueue(
                    po_no=po_no,
                    pallet_id=pallet_id,
                    barcode=d.barcode,
                    sku=sku,
                    qty_gr=qty_gr,
                    qty_putaway=qty_putaway,
                    qty_remain_putaway=remain,
                    flow_status=flow_status,
                    last_update=now,
                ))
                created_queue += 1

            d.qty_remain_putaway = remain
            d.last_update = now
            if remain <= 0:
                d.status = "DONE"

        db.flush()

        po_rows = db.query(PoDetail).all()
        for po in po_rows:
            po_no = norm(po.po_no)
            sku = upper(po.sku)
            if not po_no or not sku:
                continue
            qty_received = (
                db.query(func.coalesce(func.sum(InboundQueue.qty_gr), 0))
                .filter(
                    func.upper(func.trim(InboundQueue.po_no)) == po_no.upper(),
                    func.upper(func.trim(InboundQueue.sku)) == sku,
                )
                .scalar()
            )
            qty_received = int(qty_received or 0)
            po.qty_received = qty_received
            po.qty_remaining = max(int(po.qty_order or 0) - qty_received, 0)
            po.status = receipt_status(qty_received, int(po.qty_order or 0))
            po.last_update = now
            synced_po += 1

        db.commit()
        print("OK Sprint54 repair")
        print(f"created_queue={created_queue}")
        print(f"synced_queue={synced_queue}")
        print(f"synced_po_detail={synced_po}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
