from datetime import datetime

from sqlalchemy.orm import Session

from app.models.tables import (
    ProductMaster,
    SkuMaster,
    InboundQueue,
    PalletDetail,
    GrLog,
    InventoryBalance,
    LocationMaster,
    CategoryAisleMaster,
    PutawayLog,
    MasterDataIssue,
    AuditLog,
)

print("WAREHOUSE SERVICE LOADED:", __file__)

def product_by_barcode(db: Session, barcode: str):
    barcode = barcode.strip()
    return db.query(ProductMaster).filter(ProductMaster.barcode == barcode).first()


def get_product_scan_info(db: Session, barcode: str):
    barcode = barcode.strip()

    if not barcode:
        raise ValueError("Vui lòng scan barcode sản phẩm")

    product = product_by_barcode(db, barcode)
    if not product:
        raise ValueError("Không tìm thấy mã hàng trong danh mục sản phẩm")

    sku_master = db.query(SkuMaster).filter(SkuMaster.sku == product.sku).first()
    pcb = sku_master.pcb if sku_master and sku_master.pcb else 1

    return {
        "sku": product.sku,
        "barcode": product.barcode,
        "product_name": product.product_name or "",
        "uom": product.uom or "EA",
        "category": product.category or "",
        "pcb": int(pcb or 1),
    }


def confirm_gr(
    db: Session,
    po_no: str,
    pallet_id: str,
    barcode: str,
    carton_qty: int = 0,
    loose_qty: int = 0,
    pcb: int | None = None,
    qty_promo: int = 0,
    user_name: str = "developer",
    qty_gr: int | None = None,
):
    po_no = po_no.strip()
    pallet_id = pallet_id.strip().upper()
    barcode = barcode.strip()
    carton_qty = int(carton_qty or 0)
    loose_qty = int(loose_qty or 0)
    qty_promo = int(qty_promo or 0)

    if not po_no:
        raise ValueError("Vui lòng scan/nhập PO")

    if not pallet_id:
        raise ValueError("Vui lòng scan PA/Pallet")

    if not barcode:
        raise ValueError("Vui lòng scan barcode sản phẩm")

    if carton_qty < 0:
        raise ValueError("Số thùng chẵn không được âm")

    if loose_qty < 0:
        raise ValueError("Số kiện lẻ không được âm")

    if qty_promo < 0:
        raise ValueError("Số lượng khuyến mãi không được âm")

    product = product_by_barcode(db, barcode)
    if not product:
        raise ValueError("Không tìm thấy mã hàng trong danh mục sản phẩm")

    sku_master = db.query(SkuMaster).filter(SkuMaster.sku == product.sku).first()
    master_pcb = sku_master.pcb if sku_master and sku_master.pcb else 1
    pcb = int(pcb or master_pcb or 1)

    if pcb <= 0:
        raise ValueError("PCB phải lớn hơn 0")

    qty_base = carton_qty * pcb + loose_qty

    # Backward compatible: nếu form cũ còn gửi qty_gr thì vẫn nhận, nhưng ưu tiên công thức mới.
    if qty_base <= 0 and qty_gr is not None:
        qty_base = int(qty_gr or 0)

    qty_total = qty_base + qty_promo
    qty_gr = qty_total

    if qty_base < 0:
        raise ValueError("Số lượng nhận không được âm")

    if qty_total <= 0:
        raise ValueError("Tổng số lượng nhập phải lớn hơn 0")

    existing_pallet = (
        db.query(InboundQueue)
        .filter(InboundQueue.pallet_id == pallet_id)
        .first()
    )

    if existing_pallet:
        raise ValueError("PA/Pallet này đã được GR rồi")

    now = datetime.utcnow()

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
        qty_remain_putaway=qty_total,
        flow_status="WAIT_PUTAWAY",
        last_update=now,
    )

    pallet_detail = PalletDetail(
        pallet_id=pallet_id,
        po_no=po_no,
        barcode=barcode,
        sku=product.sku,
        qty_gr=qty_gr,
        qty_putaway=0,
        qty_remain_putaway=qty_total,
        status="WAIT_PUTAWAY",
        created_at=now,
        last_update=now,
    )

    db.add(log)
    db.add(queue)
    db.add(pallet_detail)
    db.add(AuditLog(
        operation="GR",
        reference_no=po_no,
        pallet_id=pallet_id,
        location_id="",
        sku=product.sku,
        barcode=barcode,
        qty_before=0,
        qty_after=qty_total,
        qty_change=qty_total,
        user_name=user_name,
        remark=f"Nhận hàng: PCB={pcb}, thùng chẵn={carton_qty}, kiện lẻ={loose_qty}, hàng thường={qty_base}, khuyến mãi={qty_promo}, tổng={qty_total}",
    ))
    db.commit()
    db.refresh(queue)

    return {
        "queue_id": queue.queue_id,
        "po_no": queue.po_no,
        "pallet_id": queue.pallet_id,
        "sku": queue.sku,
        "barcode": queue.barcode,
        "qty_gr": qty_base,
        "carton_qty": carton_qty,
        "loose_qty": loose_qty,
        "pcb": pcb,
        "qty_promo": qty_promo,
        "product_name": product.product_name or "",
        "qty_total": qty_total,
        "qty_remain_putaway": queue.qty_remain_putaway,
        "flow_status": queue.flow_status,
    }


def get_gr_history_by_po(db: Session, po_no: str, limit: int = 50):
    po_no = po_no.strip()

    if not po_no:
        return []

    return (
        db.query(InboundQueue)
        .filter(InboundQueue.po_no == po_no)
        .order_by(InboundQueue.queue_id.desc())
        .limit(limit)
        .all()
    )


def get_wait_putaway_tasks(db: Session):
    return (
        db.query(InboundQueue)
        .filter(InboundQueue.flow_status.in_(["WAIT_PUTAWAY", "PARTIAL"]))
        .order_by(InboundQueue.last_update.asc())
        .limit(100)
        .all()
    )


def get_putaway_by_pallet(db: Session, pallet_id: str):
    pallet_id = pallet_id.strip().upper()

    queue = (
        db.query(InboundQueue)
        .filter(
            InboundQueue.pallet_id == pallet_id,
            InboundQueue.flow_status.in_(["WAIT_PUTAWAY", "PARTIAL"]),
        )
        .first()
    )

    if not queue:
        raise ValueError("Không tìm thấy PA cần Put Away")

    product = (
        db.query(ProductMaster)
        .filter(ProductMaster.sku == queue.sku)
        .first()
    )

    category = product.category if product else ""

    suggested_aisles = (
        db.query(CategoryAisleMaster)
        .filter(CategoryAisleMaster.category == category)
        .order_by(CategoryAisleMaster.priority.asc())
        .all()
    )

    return {
        "queue_id": queue.queue_id,
        "po_no": queue.po_no,
        "pallet_id": queue.pallet_id,
        "sku": queue.sku,
        "barcode": queue.barcode,
        "category": category,
        "qty_gr": queue.qty_gr,
        "qty_putaway": queue.qty_putaway,
        "qty_remain_putaway": queue.qty_remain_putaway,
        "flow_status": queue.flow_status,
        "suggested_aisles": [
            {
                "zone": x.zone,
                "aisle": x.aisle,
                "priority": x.priority,
                "note": x.note,
            }
            for x in suggested_aisles
        ],
    }


def confirm_putaway(
    db: Session,
    queue_id: int,
    location_id: str,
    qty_putaway: int,
    user_name: str,
):
    location_id = location_id.strip().upper()

    if not location_id:
        raise ValueError("Vui lòng scan vị trí")

    if qty_putaway <= 0:
        raise ValueError("Số lượng Put Away không hợp lệ")

    try:
        queue = (
            db.query(InboundQueue)
            .filter(InboundQueue.queue_id == queue_id)
            .first()
        )

        if not queue:
            raise ValueError("Không tìm thấy task Put Away")

        if queue.flow_status not in ["WAIT_PUTAWAY", "PARTIAL"]:
            raise ValueError("Task không còn Put Away được")

        if qty_putaway > queue.qty_remain_putaway:
            raise ValueError("Số lượng Put Away vượt số lượng còn lại")

        location = (
            db.query(LocationMaster)
            .filter(LocationMaster.location_id == location_id)
            .first()
        )

        is_temp_location = False
        location_status = "ACTIVE"

        if location:
            location_status = location.status or "ACTIVE"

            if location_status == "BLOCK":
                raise ValueError("Vị trí đang bị khóa, không thể Put Away")

            if location_status == "TEMP":
                is_temp_location = True

        else:
            is_temp_location = True

            issue = MasterDataIssue(
                issue_type="LOCATION_NOT_IN_MASTER",
                sku=queue.sku,
                barcode=queue.barcode,
                pallet_id=queue.pallet_id,
                location_id=location_id,
                source_module="PUTAWAY",
                source_ref_id=str(queue.queue_id),
                created_by=user_name,
                note="Put Away vào vị trí tạm/chưa có trong location_master",
            )

            db.add(issue)

        inv = (
            db.query(InventoryBalance)
            .filter(
                InventoryBalance.sku == queue.sku,
                InventoryBalance.location_id == location_id,
            )
            .first()
        )

        if inv:
            inv.qty_onhand += qty_putaway
            inv.last_update = datetime.utcnow()
        else:
            inv = InventoryBalance(
                sku=queue.sku,
                barcode=queue.barcode,
                location_id=location_id,
                qty_onhand=qty_putaway,
                last_update=datetime.utcnow(),
            )
            db.add(inv)

        log = PutawayLog(
            queue_id=queue.queue_id,
            pallet_id=queue.pallet_id,
            sku=queue.sku,
            barcode=queue.barcode,
            location_id=location_id,
            qty_putaway=qty_putaway,
            user_name=user_name,
        )

        db.add(log)
        db.add(AuditLog(
            operation="PUTAWAY",
            reference_no=queue.po_no,
            pallet_id=queue.pallet_id,
            location_id=location_id,
            sku=queue.sku,
            barcode=queue.barcode,
            qty_before=queue.qty_remain_putaway,
            qty_after=queue.qty_remain_putaway - qty_putaway,
            qty_change=-qty_putaway,
            user_name=user_name,
            remark="Cất hàng vào vị trí",
        ))

        queue.qty_putaway += qty_putaway
        queue.qty_remain_putaway -= qty_putaway

        if queue.qty_remain_putaway == 0:
            queue.flow_status = "DONE"
        else:
            queue.flow_status = "PARTIAL"

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
            "location_status": location_status,
            "is_temp_location": is_temp_location,
        }

    except Exception:
        db.rollback()
        raise


def search_inventory(db: Session, q: str = ""):
    query = db.query(InventoryBalance)

    q = q.strip()

    if q:
        query = query.filter(
            (InventoryBalance.sku.ilike(f"%{q}%"))
            | (InventoryBalance.barcode.ilike(f"%{q}%"))
            | (InventoryBalance.location_id.ilike(f"%{q}%"))
        )

    return query.order_by(InventoryBalance.last_update.desc()).limit(100).all()