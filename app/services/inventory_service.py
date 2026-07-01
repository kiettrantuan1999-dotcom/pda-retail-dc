from datetime import datetime
from app.utils.timezone import now_vn
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.tables import (
    InventoryBalance,
    ProductMaster,
    LocationMaster,
    InventoryCountHeader,
    InventoryCountDetail,
    InventoryAdjustmentLog,
    OperationLog,
    AuditLog,
)


def _now():
    return now_vn()


def _clean_code(value: str) -> str:
    return (value or "").strip().upper()


def make_count_no() -> str:
    return "CC" + now_vn().strftime("%Y%m%d%H%M%S")


def search_inventory(db: Session, q: str = ""):
    q = (q or "").strip()

    query = (
        db.query(InventoryBalance, ProductMaster.product_name)
        .outerjoin(ProductMaster, ProductMaster.sku == InventoryBalance.sku)
    )

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                InventoryBalance.sku.ilike(like),
                InventoryBalance.barcode.ilike(like),
                InventoryBalance.location_id.ilike(like),
                ProductMaster.product_name.ilike(like),
            )
        )

    rows = query.order_by(InventoryBalance.location_id.asc(), InventoryBalance.sku.asc()).limit(200).all()

    return [
        {
            "inventory_id": inv.inventory_id,
            "sku": inv.sku,
            "barcode": inv.barcode,
            "product_name": product_name or "",
            "location_id": inv.location_id,
            "qty_onhand": inv.qty_onhand,
            "last_update": inv.last_update.strftime("%Y-%m-%d %H:%M:%S") if inv.last_update else "",
        }
        for inv, product_name in rows
    ]


def list_counts(db: Session):
    return (
        db.query(InventoryCountHeader)
        .order_by(InventoryCountHeader.count_id.desc())
        .limit(100)
        .all()
    )


def get_count_header(db: Session, count_no: str):
    count_no = _clean_code(count_no)
    header = db.query(InventoryCountHeader).filter(InventoryCountHeader.count_no == count_no).first()
    if not header:
        raise ValueError("Không tìm thấy đợt kiểm kê")
    return header


def refresh_count_summary(db: Session, count_no: str):
    header = get_count_header(db, count_no)

    total_lines = db.query(InventoryCountDetail).filter(InventoryCountDetail.count_no == header.count_no).count()
    counted_lines = (
        db.query(InventoryCountDetail)
        .filter(InventoryCountDetail.count_no == header.count_no, InventoryCountDetail.status == "DONE")
        .count()
    )
    variance_lines = (
        db.query(InventoryCountDetail)
        .filter(InventoryCountDetail.count_no == header.count_no, InventoryCountDetail.status == "DONE", InventoryCountDetail.variance_qty != 0)
        .count()
    )
    total_locations = (
        db.query(InventoryCountDetail.location_id)
        .filter(InventoryCountDetail.count_no == header.count_no)
        .distinct()
        .count()
    )

    header.total_lines = total_lines
    header.counted_lines = counted_lines
    header.variance_lines = variance_lines
    header.total_locations = total_locations
    header.last_update = _now()

    if header.status == "OPEN" and total_lines > 0 and counted_lines == total_lines:
        header.status = "COUNTED"

    return header


def create_count(db: Session, count_name: str, locations_text: str, created_by: str):
    raw_locations = [x.strip().upper() for x in (locations_text or "").replace(",", "\n").splitlines() if x.strip()]
    locations = sorted(set(raw_locations))

    if not locations:
        raise ValueError("Vui lòng nhập ít nhất 1 vị trí cần kiểm kê")

    count_no = make_count_no()
    header = InventoryCountHeader(
        count_no=count_no,
        count_name=(count_name or "").strip() or f"Kiểm kê {count_no}",
        status="OPEN",
        created_by=created_by,
    )
    db.add(header)

    inv_rows = (
        db.query(InventoryBalance, ProductMaster.product_name)
        .outerjoin(ProductMaster, ProductMaster.sku == InventoryBalance.sku)
        .filter(InventoryBalance.location_id.in_(locations))
        .order_by(InventoryBalance.location_id.asc(), InventoryBalance.sku.asc())
        .all()
    )

    if not inv_rows:
        raise ValueError("Không tìm thấy tồn hệ thống tại các vị trí đã nhập")

    for inv, product_name in inv_rows:
        db.add(
            InventoryCountDetail(
                count_no=count_no,
                location_id=inv.location_id,
                sku=inv.sku,
                barcode=inv.barcode,
                product_name=product_name or "",
                expected_qty=inv.qty_onhand or 0,
                status="WAIT_COUNT",
            )
        )

    db.flush()
    refresh_count_summary(db, count_no)

    db.add(OperationLog(
        event_type="CREATE_COUNT",
        module_name="INVENTORY",
        user_name=created_by,
        reference_type="COUNT_NO",
        reference_id=count_no,
        status="SUCCESS",
        message=f"Tạo đợt kiểm kê {count_no}",
    ))

    db.commit()
    return get_count_header(db, count_no)


def get_count_details(db: Session, count_no: str, location_id: str = "", status: str = ""):
    count_no = _clean_code(count_no)
    query = db.query(InventoryCountDetail).filter(InventoryCountDetail.count_no == count_no)

    if location_id:
        query = query.filter(InventoryCountDetail.location_id == _clean_code(location_id))

    if status:
        query = query.filter(InventoryCountDetail.status == status.strip().upper())

    return query.order_by(InventoryCountDetail.location_id.asc(), InventoryCountDetail.sku.asc()).all()


def get_count_task_by_scan(db: Session, count_no: str, location_id: str, barcode: str):
    count_no = _clean_code(count_no)
    location_id = _clean_code(location_id)
    barcode = (barcode or "").strip()

    if not location_id:
        raise ValueError("Vui lòng scan vị trí")
    if not barcode:
        raise ValueError("Vui lòng scan barcode")

    detail = (
        db.query(InventoryCountDetail)
        .filter(
            InventoryCountDetail.count_no == count_no,
            InventoryCountDetail.location_id == location_id,
            InventoryCountDetail.barcode == barcode,
        )
        .first()
    )

    if not detail:
        raise ValueError("Barcode này không nằm trong task kiểm kê của vị trí đã scan")

    return detail


def save_count_result(db: Session, detail_id: int, count_qty: int, user_name: str, note: str = ""):
    if count_qty < 0:
        raise ValueError("Số lượng đếm không được âm")

    detail = db.query(InventoryCountDetail).filter(InventoryCountDetail.detail_id == detail_id).first()
    if not detail:
        raise ValueError("Không tìm thấy dòng kiểm kê")

    header = get_count_header(db, detail.count_no)
    if header.status == "APPROVED":
        raise ValueError("Đợt kiểm kê đã duyệt, không thể sửa")

    detail.count_qty = count_qty
    detail.variance_qty = count_qty - (detail.expected_qty or 0)
    detail.status = "DONE"
    detail.counted_by = user_name
    detail.counted_at = _now()
    detail.note = note or ""
    detail.last_update = _now()

    refresh_count_summary(db, detail.count_no)

    db.add(OperationLog(
        event_type="SAVE_COUNT",
        module_name="INVENTORY",
        user_name=user_name,
        reference_type="COUNT_DETAIL",
        reference_id=str(detail.detail_id),
        status="SUCCESS",
        message=f"Kiểm kê {detail.location_id} / {detail.sku}: {count_qty}",
    ))
    db.add(AuditLog(
        operation="COUNT",
        reference_no=detail.count_no,
        pallet_id="",
        location_id=detail.location_id,
        sku=detail.sku,
        barcode=detail.barcode,
        qty_before=detail.expected_qty or 0,
        qty_after=count_qty,
        qty_change=count_qty - (detail.expected_qty or 0),
        user_name=user_name,
        remark=note or "Kiểm kê tồn",
    ))

    db.commit()
    db.refresh(detail)
    return detail


def approve_count(db: Session, count_no: str, approved_by: str):
    header = get_count_header(db, count_no)

    if header.status == "APPROVED":
        raise ValueError("Đợt kiểm kê đã được duyệt trước đó")

    details = get_count_details(db, header.count_no)
    if not details:
        raise ValueError("Đợt kiểm kê chưa có dòng chi tiết")

    pending = [d for d in details if d.status != "DONE"]
    if pending:
        raise ValueError("Còn dòng chưa kiểm kê, không thể duyệt")

    for d in details:
        inv = (
            db.query(InventoryBalance)
            .filter(InventoryBalance.sku == d.sku, InventoryBalance.location_id == d.location_id)
            .first()
        )

        qty_before = inv.qty_onhand if inv else 0
        qty_after = d.count_qty or 0

        if inv:
            inv.qty_onhand = qty_after
            inv.last_update = _now()
        else:
            inv = InventoryBalance(
                sku=d.sku,
                barcode=d.barcode,
                location_id=d.location_id,
                qty_onhand=qty_after,
                last_update=_now(),
            )
            db.add(inv)

        if qty_before != qty_after:
            db.add(InventoryAdjustmentLog(
                count_no=header.count_no,
                sku=d.sku,
                barcode=d.barcode,
                location_id=d.location_id,
                qty_before=qty_before,
                qty_after=qty_after,
                variance_qty=qty_after - qty_before,
                reason="CYCLE_COUNT_APPROVAL",
                created_by=approved_by,
            ))
            db.add(AuditLog(
                operation="ADJUST",
                reference_no=header.count_no,
                pallet_id="",
                location_id=d.location_id,
                sku=d.sku,
                barcode=d.barcode,
                qty_before=qty_before,
                qty_after=qty_after,
                qty_change=qty_after - qty_before,
                user_name=approved_by,
                remark="Điều chỉnh tồn sau duyệt kiểm kê",
            ))

    header.status = "APPROVED"
    header.approved_by = approved_by
    header.approved_at = _now()
    header.last_update = _now()

    db.add(OperationLog(
        event_type="APPROVE_COUNT",
        module_name="INVENTORY",
        user_name=approved_by,
        reference_type="COUNT_NO",
        reference_id=header.count_no,
        status="SUCCESS",
        message=f"Duyệt kiểm kê {header.count_no}",
    ))

    db.commit()
    db.refresh(header)
    return header
