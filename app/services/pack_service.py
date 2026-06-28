from datetime import datetime

from sqlalchemy.orm import Session

from app.models.tables import (
    PickingHeader,
    PickingDetail,
    PackHeader,
    PackLog,
    DoDetail,
    AuditLog,
)


def _find_picking_header(db: Session, scan_code: str):
    scan_code = scan_code.strip().upper()

    header = (
        db.query(PickingHeader)
        .filter(PickingHeader.picking_no == scan_code)
        .first()
    )

    if header:
        return header

    return (
        db.query(PickingHeader)
        .filter(PickingHeader.do_no == scan_code)
        .first()
    )


def get_pack_by_do(db: Session, do_no: str):
    do_no = do_no.strip().upper()

    header = _find_picking_header(db, do_no)

    if not header:
        return {
            "ok": False,
            "message": f"Không tìm thấy DO/Picking: {do_no}",
        }

    if header.pack_status == "DONE":
        return {
            "ok": False,
            "message": "Phiếu đã được đóng hàng.",
        }

    details = (
        db.query(PickingDetail)
        .filter(PickingDetail.picking_id == header.picking_id)
        .all()
    )

    total_qty = sum(int(x.qty_pick or 0) for x in details)
    sku_line_count = len(details)

    return {
        "ok": True,
        "picking_id": header.picking_id,
        "picking_no": header.picking_no,
        "do_no": header.do_no,
        "store_id": header.store_id,
        "store_name": header.store_name or "",
        "pack_type": header.pick_type,
        "pack_type_name": header.pick_type,
        "status": header.pack_status or "WAIT",
        "sku_line_count": sku_line_count,
        "total_qty": total_qty,
        "actual_package_qty": int(header.carton_qty or 0),
        "rows": [
            {
                "sku": x.sku,
                "barcode": x.barcode,
                "product_name": x.product_name,
                "qty_pick": int(x.qty_pick or 0),
            }
            for x in details
        ],
    }


def confirm_pack(
    db: Session,
    do_no: str,
    actual_package_qty: int,
    user_name: str = "",
    device_name: str = "",
):
    do_no = do_no.strip().upper()

    header = _find_picking_header(db, do_no)

    if not header:
        return {
            "ok": False,
            "message": f"Không tìm thấy DO/Picking: {do_no}",
        }

    if header.pack_status == "DONE":
        return {
            "ok": False,
            "message": "Phiếu này đã được đóng hàng.",
        }

    details = (
        db.query(PickingDetail)
        .filter(PickingDetail.picking_id == header.picking_id)
        .all()
    )

    if not details:
        return {
            "ok": False,
            "message": f"Phiếu {header.picking_no} chưa có detail để pack.",
        }

    if actual_package_qty <= 0 or actual_package_qty > 999:
        return {
            "ok": False,
            "message": "Số kiện thực tế không hợp lệ.",
        }

    total_qty = sum(int(x.qty_pick or 0) for x in details)
    sku_line_count = len(details)
    now = datetime.utcnow()

    header.pack_status = "DONE"
    header.packed_by = user_name or ""
    header.packed_time = now
    header.carton_qty = actual_package_qty
    header.last_update = now

    for row in details:
        row.pack_status = "DONE"

    pack_header = (
        db.query(PackHeader)
        .filter(PackHeader.picking_no == header.picking_no)
        .first()
    )

    if pack_header:
        pack_header.status = "DONE"
        pack_header.actual_package_qty = actual_package_qty
        pack_header.packed_by = user_name or ""
        pack_header.packed_at = now
        pack_header.last_update = now
    else:
        pack_header = PackHeader(
            picking_id=header.picking_id,
            picking_no=header.picking_no,
            do_no=header.do_no,
            store_id=header.store_id,
            store_name=header.store_name or "",
            pack_type=header.pick_type,
            sku_line_count=sku_line_count,
            total_qty=total_qty,
            actual_package_qty=actual_package_qty,
            status="DONE",
            packed_by=user_name or "",
            packed_at=now,
            created_at=now,
            last_update=now,
        )
        db.add(pack_header)

    do_rows = (
        db.query(DoDetail)
        .filter(DoDetail.do_no == header.do_no)
        .all()
    )

    for row in do_rows:
        row.qty_packed = row.qty_do
        row.qty_remain = 0
        row.status = "PACKED"

    log = PackLog(
        picking_no=header.picking_no,
        do_no=header.do_no,
        store_id=header.store_id,
        pack_type=header.pick_type,
        sku_line_count=sku_line_count,
        total_qty=total_qty,
        actual_package_qty=actual_package_qty,
        action="CONFIRM_PACK",
        user_name=user_name or "",
        device_name=device_name or "",
        created_at=now,
    )
    db.add(log)
    db.add(AuditLog(
        operation="PACK",
        reference_no=header.do_no,
        pallet_id="",
        location_id="",
        sku="",
        barcode="",
        qty_before=0,
        qty_after=total_qty,
        qty_change=-total_qty,
        user_name=user_name or "",
        remark=f"Đóng hàng {header.picking_no} / {actual_package_qty} kiện",
    ))

    db.commit()

    return {
        "ok": True,
        "message": f"Đã pack xong phiếu {header.picking_no}",
        "picking_id": header.picking_id,
        "picking_no": header.picking_no,
        "do_no": header.do_no,
        "store_id": header.store_id,
        "store_name": header.store_name or "",
        "pack_type": header.pick_type,
        "pack_status": header.pack_status,
        "sku_line_count": sku_line_count,
        "total_qty": total_qty,
        "actual_package_qty": actual_package_qty,
    }


def get_pack_logs(db: Session, limit: int = 100):
    logs = (
        db.query(PackLog)
        .order_by(PackLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "pack_log_id": x.pack_id,
            "picking_no": x.picking_no,
            "do_no": x.do_no,
            "store_id": x.store_id,
            "pack_type": x.pack_type,
            "sku_line_count": x.sku_line_count,
            "total_qty": x.total_qty,
            "actual_package_qty": x.actual_package_qty,
            "action": x.action,
            "user_name": x.user_name,
            "device_name": x.device_name,
            "created_at": x.created_at,
        }
        for x in logs
    ]