from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.tables import (
    ProductMaster, InboundQueue, GrLog, InventoryBalance
)


def product_by_barcode(db: Session, barcode: str):
    return db.query(ProductMaster).filter(ProductMaster.barcode == barcode).first()


def confirm_gr(db: Session, po_no: str, pallet_id: str, barcode: str, qty_gr: int, user_name: str):
    if qty_gr <= 0:
        raise ValueError("Số lượng nhận phải lớn hơn 0")

    product = product_by_barcode(db, barcode)
    if not product:
        raise ValueError("Không tìm thấy mã hàng trong danh mục sản phẩm")

    # Check pallet trùng
    existing_pallet = (
        db.query(InboundQueue)
        .filter(InboundQueue.pallet_id == pallet_id)
        .first()
    )

    if existing_pallet:
        raise ValueError("PA/Pallet này đã được GR rồi")

    log = GrLog(
        po_no=po_no,
        pallet_id=pallet_id,
        barcode=barcode,
        sku=product.sku,
        qty_gr=qty_gr,
        user_name=user_name,
    )

    queue = InboundQueue(
        po_no=po_no,
        pallet_id=pallet_id,
        barcode=barcode,
        sku=product.sku,
        qty_gr=qty_gr,
        qty_putaway=0,
        qty_remain_putaway=qty_gr,
        flow_status="WAIT_PUTAWAY",
        last_update=datetime.utcnow(),
    )

    db.add(log)
    db.add(queue)
    db.commit()
    db.refresh(queue)

    return {
        "queue_id": queue.queue_id,
        "po_no": po_no,
        "pallet_id": pallet_id,
        "sku": product.sku,
        "barcode": barcode,
        "qty_gr": qty_gr,
        "flow_status": "WAIT_PUTAWAY",
    }
def get_wait_putaway_tasks(db: Session):
    return (
        db.query(InboundQueue)
        .filter(InboundQueue.flow_status == "WAIT_PUTAWAY")
        .order_by(InboundQueue.last_update.asc())
        .limit(100)
        .all()
    )
def confirm_putaway(db: Session, queue_id: int, location_id: str, qty_putaway: int, user_name: str):
    queue = (
        db.query(InboundQueue)
        .filter(InboundQueue.queue_id == queue_id)
        .first()
    )

    if not queue:
        raise ValueError("Không tìm thấy task Put Away")

    if queue.flow_status != "WAIT_PUTAWAY":
        raise ValueError("Task này không còn trạng thái WAIT_PUTAWAY")

    if qty_putaway <= 0:
        raise ValueError("Số lượng put away phải lớn hơn 0")

    if qty_putaway > queue.qty_remain_putaway:
        raise ValueError("Số lượng put away vượt số lượng còn lại")

    inv = (
        db.query(InventoryBalance)
        .filter(
            InventoryBalance.sku == queue.sku,
            InventoryBalance.barcode == queue.barcode,
            InventoryBalance.location_id == location_id,
        )
        .first()
    )

    if inv:
        inv.qty_onhand += qty_putaway
    else:
        inv = InventoryBalance(
            sku=queue.sku,
            barcode=queue.barcode,
            location_id=location_id,
            qty_onhand=qty_putaway,
        )
        db.add(inv)

    queue.qty_putaway += qty_putaway
    queue.qty_remain_putaway -= qty_putaway

    if queue.qty_remain_putaway == 0:
        queue.flow_status = "DONE"

    queue.last_update = datetime.utcnow()

    db.commit()
    db.refresh(queue)

    return {
        "queue_id": queue.queue_id,
        "pallet_id": queue.pallet_id,
        "sku": queue.sku,
        "barcode": queue.barcode,
        "location_id": location_id,
        "qty_putaway": qty_putaway,
        "qty_remain_putaway": queue.qty_remain_putaway,
        "flow_status": queue.flow_status,
    }
