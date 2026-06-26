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

    return {"queue_id": queue.queue_id, "sku": product.sku, "qty_gr": qty_gr}


def search_inventory(db: Session, q: str):
    query = db.query(InventoryBalance)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (InventoryBalance.sku.ilike(like)) |
            (InventoryBalance.barcode.ilike(like)) |
            (InventoryBalance.location_id.ilike(like))
        )
    return query.order_by(InventoryBalance.location_id.asc(), InventoryBalance.sku.asc()).limit(200).all()
