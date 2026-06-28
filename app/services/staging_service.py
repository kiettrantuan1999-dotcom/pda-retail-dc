from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.tables import (
    AuditLog,
    DoDetail,
    PackHeader,
    PickingHeader,
)


def _clean_do_no(value: str) -> str:
    return (value or "").strip().upper()


def _resolve_do_no(db: Session, scan_code: str) -> str:
    scan_code = _clean_do_no(scan_code)
    if not scan_code:
        return ""

    header = (
        db.query(PickingHeader)
        .filter(PickingHeader.picking_no == scan_code)
        .first()
    )
    if header:
        return header.do_no

    return scan_code


def _pack_type_label(pack_type: str) -> str:
    value = (pack_type or "").upper()
    if value == "CASE":
        return "Hàng chẵn"
    if value == "ODD":
        return "Hàng lẻ"
    return pack_type or "Khác"


def _is_even_pack(pack_type: str) -> bool:
    return (pack_type or "").upper() == "CASE"


def _is_odd_pack(pack_type: str) -> bool:
    return (pack_type or "").upper() == "ODD"


def get_staging_summary(db: Session, scan_code: str):
    do_no = _resolve_do_no(db, scan_code)

    if not do_no:
        return {
            "ok": False,
            "message": "Vui lòng nhập hoặc scan mã DO.",
        }

    picking_headers = (
        db.query(PickingHeader)
        .filter(PickingHeader.do_no == do_no)
        .order_by(PickingHeader.pick_type.asc())
        .all()
    )

    if not picking_headers:
        return {
            "ok": False,
            "message": f"Không tìm thấy phiếu lấy hàng cho DO {do_no}.",
        }

    not_packed = [h.picking_no for h in picking_headers if (h.pack_status or "") != "DONE"]
    if not_packed:
        return {
            "ok": False,
            "message": "DO chưa đóng hàng đủ. Phiếu còn chờ đóng: " + ", ".join(not_packed),
        }

    pack_headers = (
        db.query(PackHeader)
        .filter(PackHeader.do_no == do_no)
        .order_by(PackHeader.pack_type.asc(), PackHeader.picking_no.asc())
        .all()
    )

    if not pack_headers:
        return {
            "ok": False,
            "message": f"DO {do_no} đã có picking nhưng chưa có dữ liệu đóng hàng.",
        }

    store_id = pack_headers[0].store_id or ""
    store_name = pack_headers[0].store_name or ""
    packed_by = ", ".join(sorted({p.packed_by for p in pack_headers if p.packed_by}))
    packed_at_values = [p.packed_at for p in pack_headers if p.packed_at]
    last_packed_at = max(packed_at_values) if packed_at_values else None

    total_package = sum(int(p.actual_package_qty or 0) for p in pack_headers)
    even_package = sum(int(p.actual_package_qty or 0) for p in pack_headers if _is_even_pack(p.pack_type))
    odd_package = sum(int(p.actual_package_qty or 0) for p in pack_headers if _is_odd_pack(p.pack_type))
    total_qty = sum(int(p.total_qty or 0) for p in pack_headers)
    total_sku_line = sum(int(p.sku_line_count or 0) for p in pack_headers)

    staging_statuses = {(p.staging_status or "WAIT") for p in pack_headers}
    staging_status = "DONE" if staging_statuses == {"DONE"} else "WAIT"
    confirm_users = ", ".join(sorted({p.staging_confirm_user for p in pack_headers if p.staging_confirm_user}))
    confirm_times = [p.staging_confirm_time for p in pack_headers if p.staging_confirm_time]
    confirm_time = max(confirm_times) if confirm_times else None

    lines = [
        {
            "picking_no": p.picking_no,
            "pack_type": p.pack_type,
            "pack_type_name": _pack_type_label(p.pack_type),
            "sku_line_count": int(p.sku_line_count or 0),
            "total_qty": int(p.total_qty or 0),
            "actual_package_qty": int(p.actual_package_qty or 0),
            "packed_by": p.packed_by or "",
            "packed_at": p.packed_at,
            "staging_status": p.staging_status or "WAIT",
        }
        for p in pack_headers
    ]

    return {
        "ok": True,
        "do_no": do_no,
        "store_id": store_id,
        "store_name": store_name,
        "total_package": total_package,
        "even_package": even_package,
        "odd_package": odd_package,
        "total_qty": total_qty,
        "total_sku_line": total_sku_line,
        "packed_by": packed_by,
        "last_packed_at": last_packed_at,
        "staging_status": staging_status,
        "confirm_user": confirm_users,
        "confirm_time": confirm_time,
        "lines": lines,
    }


def list_wait_staging(db: Session, limit: int = 100):
    pack_rows = (
        db.query(PackHeader)
        .filter(PackHeader.status == "DONE")
        .order_by(PackHeader.packed_at.desc().nullslast(), PackHeader.pack_id.desc())
        .limit(1000)
        .all()
    )

    grouped = defaultdict(list)
    for p in pack_rows:
        grouped[p.do_no].append(p)

    rows = []
    for do_no, items in grouped.items():
        if not do_no:
            continue

        picking_headers = db.query(PickingHeader).filter(PickingHeader.do_no == do_no).all()
        if not picking_headers:
            continue
        if any((h.pack_status or "") != "DONE" for h in picking_headers):
            continue

        if all((p.staging_status or "WAIT") == "DONE" for p in items):
            continue

        rows.append({
            "do_no": do_no,
            "store_id": items[0].store_id or "",
            "store_name": items[0].store_name or "",
            "total_package": sum(int(p.actual_package_qty or 0) for p in items),
            "even_package": sum(int(p.actual_package_qty or 0) for p in items if _is_even_pack(p.pack_type)),
            "odd_package": sum(int(p.actual_package_qty or 0) for p in items if _is_odd_pack(p.pack_type)),
            "total_qty": sum(int(p.total_qty or 0) for p in items),
            "total_sku_line": sum(int(p.sku_line_count or 0) for p in items),
            "last_packed_at": max([p.packed_at for p in items if p.packed_at], default=None),
        })

    rows.sort(key=lambda x: x["last_packed_at"] or datetime.min, reverse=True)
    return rows[:limit]


def confirm_staging(
    db: Session,
    scan_code: str,
    user_name: str = "",
    remark: str = "",
):
    summary = get_staging_summary(db, scan_code)
    if not summary.get("ok"):
        return summary

    if summary.get("staging_status") == "DONE":
        return {
            "ok": False,
            "message": f"DO {summary['do_no']} đã xác nhận tập kết trước đó.",
        }

    do_no = summary["do_no"]
    now = datetime.utcnow()

    pack_headers = db.query(PackHeader).filter(PackHeader.do_no == do_no).all()
    for p in pack_headers:
        p.staging_status = "DONE"
        p.staging_confirm_user = user_name or ""
        p.staging_confirm_time = now
        p.staging_remark = remark or ""
        p.last_update = now

    do_rows = db.query(DoDetail).filter(DoDetail.do_no == do_no).all()
    for row in do_rows:
        row.status = "DONE"

    db.add(AuditLog(
        operation="STAGING_CONFIRM",
        reference_no=do_no,
        pallet_id="",
        location_id="",
        sku="",
        barcode="",
        qty_before=int(summary.get("total_package") or 0),
        qty_after=int(summary.get("total_package") or 0),
        qty_change=0,
        user_name=user_name or "",
        remark=(
            f"Xác nhận tập kết DO {do_no}: "
            f"Tổng {summary.get('total_package', 0)} kiện, "
            f"chẵn {summary.get('even_package', 0)}, "
            f"lẻ {summary.get('odd_package', 0)}. "
            f"{remark or ''}"
        ).strip(),
    ))

    db.commit()

    summary = get_staging_summary(db, do_no)
    summary["message"] = f"Đã xác nhận tập kết DO {do_no}."
    return summary
