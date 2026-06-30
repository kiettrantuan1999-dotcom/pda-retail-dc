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


def _clean_scan_code(value: str) -> str:
    return (value or "").strip().upper()


def _find_picking_header(db: Session, scan_code: str):
    """
    Flow mới: nhân viên scan barcode trên phiếu Picking List.
    Barcode = picking_header.picking_no, ví dụ: 30062026-0000002ACV-C.

    Vẫn giữ fallback scan DO để không vỡ dữ liệu/test cũ, nhưng ưu tiên picking_no.
    """
    scan_code = _clean_scan_code(scan_code)
    if not scan_code:
        return None

    header = (
        db.query(PickingHeader)
        .filter(PickingHeader.picking_no == scan_code)
        .first()
    )
    if header:
        return header

    # Fallback cũ: DO-C/DO-L hoặc DO tổng nếu còn dữ liệu cũ.
    return (
        db.query(PickingHeader)
        .filter(PickingHeader.do_no == scan_code)
        .first()
    )


def _pack_type_label(pack_type: str) -> str:
    value = (pack_type or "").upper()
    if value == "CASE":
        return "Hàng chẵn"
    if value == "ODD":
        return "Hàng lẻ"
    return pack_type or "Khác"


def _unique_do_nos(details) -> list[str]:
    values = []
    seen = set()
    for d in details:
        do_no = _clean_scan_code(getattr(d, "do_no", ""))
        if not do_no or do_no in seen or do_no == "STORE_PICKING":
            continue
        values.append(do_no)
        seen.add(do_no)
    return values


def get_pack_by_do(db: Session, do_no: str):
    scan_code = _clean_scan_code(do_no)
    header = _find_picking_header(db, scan_code)

    if not header:
        return {
            "ok": False,
            "message": f"Không tìm thấy phiếu lấy hàng: {scan_code}",
        }

    if header.pack_status == "DONE":
        return {
            "ok": False,
            "message": "Phiếu này đã được đóng hàng.",
        }

    details = (
        db.query(PickingDetail)
        .filter(PickingDetail.picking_id == header.picking_id)
        .order_by(PickingDetail.pick_index.asc(), PickingDetail.sku.asc())
        .all()
    )

    total_qty = sum(int(x.qty_pick or 0) for x in details)
    sku_line_count = len(details)
    do_nos = _unique_do_nos(details)

    pack_header = (
        db.query(PackHeader)
        .filter(PackHeader.picking_no == header.picking_no)
        .first()
    )

    return {
        "ok": True,
        "scan_code": scan_code,
        "picking_id": header.picking_id,
        "picking_no": header.picking_no,
        "do_no": header.do_no,
        "do_nos": do_nos,
        "total_do": len(do_nos),
        "store_id": header.store_id,
        "store_name": header.store_name or "",
        "trip_no": getattr(header, "trip_no", "") or "",
        "wave": getattr(header, "wave", "") or "",
        "khung_gio": getattr(header, "khung_gio", "") or "",
        "loai_giao": getattr(header, "loai_giao", "") or "",
        "pack_type": header.pick_type,
        "pack_type_name": _pack_type_label(header.pick_type),
        "status": header.pack_status or "WAIT",
        "sku_line_count": sku_line_count,
        "total_qty": total_qty,
        "actual_package_qty": int(header.carton_qty or 0),
        "picked_by": getattr(pack_header, "picked_by", "") if pack_header else "",
        "packed_by": getattr(pack_header, "packed_by", "") if pack_header else "",
        "rows": [
            {
                "location_id": x.location_id or "",
                "sku": x.sku,
                "barcode": x.barcode,
                "product_name": x.product_name,
                "uom": getattr(x, "uom", "") or "",
                "pcb": int(x.pcb or 0),
                "qty_pick": int(x.qty_pick or 0),
            }
            for x in details
        ],
    }


def confirm_pack(
    db: Session,
    do_no: str,
    actual_package_qty: int,
    picker_name: str = "",
    user_name: str = "",
    device_name: str = "",
):
    scan_code = _clean_scan_code(do_no)
    header = _find_picking_header(db, scan_code)

    if not header:
        return {
            "ok": False,
            "message": f"Không tìm thấy phiếu lấy hàng: {scan_code}",
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

    picker_name = (picker_name or "").strip()
    if not picker_name:
        return {
            "ok": False,
            "message": "Vui lòng nhập người lấy hàng / picker trước khi xác nhận đóng hàng.",
        }

    if actual_package_qty <= 0 or actual_package_qty > 999:
        return {
            "ok": False,
            "message": "Số kiện thực tế không hợp lệ.",
        }

    total_qty = sum(int(x.qty_pick or 0) for x in details)
    sku_line_count = len(details)
    do_nos = _unique_do_nos(details)
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

    # PackHeader dùng picking_no làm mã scan chính. do_no giữ để trace/fallback, không dùng để scan nữa.
    trace_do_no = ",".join(do_nos) if do_nos else (header.do_no or "")

    if pack_header:
        pack_header.do_no = trace_do_no
        pack_header.store_id = header.store_id
        pack_header.store_name = header.store_name or ""
        pack_header.pack_type = header.pick_type
        pack_header.sku_line_count = sku_line_count
        pack_header.total_qty = total_qty
        pack_header.status = "DONE"
        pack_header.actual_package_qty = actual_package_qty
        pack_header.picked_by = picker_name
        pack_header.packed_by = user_name or ""
        pack_header.packed_at = now
        pack_header.last_update = now
    else:
        pack_header = PackHeader(
            picking_id=header.picking_id,
            picking_no=header.picking_no,
            do_no=trace_do_no,
            store_id=header.store_id,
            store_name=header.store_name or "",
            pack_type=header.pick_type,
            sku_line_count=sku_line_count,
            total_qty=total_qty,
            actual_package_qty=actual_package_qty,
            status="DONE",
            picked_by=picker_name,
            packed_by=user_name or "",
            packed_at=now,
            created_at=now,
            last_update=now,
        )
        db.add(pack_header)

    # Flow mới: header.do_no = STORE_PICKING, nên phải update theo DO thật trong PickingDetail.
    if do_nos:
        do_rows = db.query(DoDetail).filter(DoDetail.do_no.in_(do_nos)).all()
        for row in do_rows:
            row.qty_packed = row.qty_do
            row.qty_remain = 0
            row.status = "PACKED"

    log = PackLog(
        picking_no=header.picking_no,
        do_no=trace_do_no,
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
        reference_no=header.picking_no,
        pallet_id="",
        location_id="",
        sku="",
        barcode="",
        qty_before=0,
        qty_after=total_qty,
        qty_change=-total_qty,
        user_name=user_name or "",
        remark=f"Đóng hàng phiếu {header.picking_no} / picker {picker_name} / packer {user_name or ''} / {actual_package_qty} kiện / {len(do_nos)} DO",
    ))

    db.commit()

    return {
        "ok": True,
        "message": f"Đã pack xong phiếu {header.picking_no}",
        "picking_id": header.picking_id,
        "picking_no": header.picking_no,
        "do_no": trace_do_no,
        "do_nos": do_nos,
        "total_do": len(do_nos),
        "store_id": header.store_id,
        "store_name": header.store_name or "",
        "pack_type": header.pick_type,
        "pack_status": header.pack_status,
        "sku_line_count": sku_line_count,
        "total_qty": total_qty,
        "actual_package_qty": actual_package_qty,
        "picked_by": picker_name,
        "packed_by": user_name or "",
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
            "pack_log_id": x.pack_log_id,
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
