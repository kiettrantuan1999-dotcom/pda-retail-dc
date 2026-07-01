from datetime import datetime
from app.utils.timezone import now_vn
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.tables import (
    AuditLog,
    DoDetail,
    PackHeader,
    PickingHeader,
    PickingDetail,
)

STORE_PICKING_DO_MARKER = "STORE_PICKING"


def _clean_code(value: str) -> str:
    return (value or "").strip().upper()


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


def _join_distinct(values) -> str:
    cleaned = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return ", ".join(cleaned)


def _same_store_wave_headers(db: Session, header: PickingHeader):
    """
    Scan 1 barcode picking list nhưng tập kết phải nhìn cả bộ phiếu của cùng cửa hàng.
    Nếu phiếu có trip/wave/slot/loại giao thì gom trong cùng nhóm đó để tránh lẫn chuyến.
    """
    q = db.query(PickingHeader).filter(PickingHeader.store_id == header.store_id)

    # Với flow mới, do_no là STORE_PICKING. Giữ filter này để tránh lẫn dữ liệu cũ theo DO.
    q = q.filter(PickingHeader.do_no == (header.do_no or STORE_PICKING_DO_MARKER))

    for attr in ["trip_no", "wave", "khung_gio", "loai_giao"]:
        value = getattr(header, attr, "") or ""
        if value:
            q = q.filter(getattr(PickingHeader, attr) == value)

    return q.order_by(PickingHeader.pick_type.asc(), PickingHeader.picking_no.asc()).all()


def _resolve_picking_headers(db: Session, scan_code: str):
    scan_code = _clean_code(scan_code)
    if not scan_code:
        return [], "", "Vui lòng nhập hoặc scan mã phiếu lấy hàng."

    header = db.query(PickingHeader).filter(PickingHeader.picking_no == scan_code).first()
    if header:
        headers = _same_store_wave_headers(db, header)
        return headers, header.picking_no, ""

    # Fallback cũ: nếu người dùng nhập store hoặc DO thì vẫn cố tìm để không mất dữ liệu test cũ.
    headers = (
        db.query(PickingHeader)
        .filter(PickingHeader.store_id == scan_code)
        .order_by(PickingHeader.pick_type.asc(), PickingHeader.picking_no.asc())
        .all()
    )
    if headers:
        return headers, scan_code, ""

    headers = (
        db.query(PickingHeader)
        .filter(PickingHeader.do_no == scan_code)
        .order_by(PickingHeader.pick_type.asc(), PickingHeader.picking_no.asc())
        .all()
    )
    if headers:
        return headers, scan_code, ""

    return [], scan_code, f"Không tìm thấy phiếu lấy hàng: {scan_code}."


def _do_nos_for_headers(db: Session, headers) -> list[str]:
    picking_ids = [h.picking_id for h in headers]
    if not picking_ids:
        return []
    rows = (
        db.query(PickingDetail.do_no)
        .filter(PickingDetail.picking_id.in_(picking_ids))
        .distinct()
        .all()
    )
    values = []
    for (do_no,) in rows:
        do_no = _clean_code(do_no)
        if do_no and do_no != STORE_PICKING_DO_MARKER:
            values.append(do_no)
    return sorted(set(values))


def get_staging_summary(db: Session, scan_code: str):
    headers, reference_code, error = _resolve_picking_headers(db, scan_code)

    if error:
        return {"ok": False, "message": error}

    if not headers:
        return {
            "ok": False,
            "message": f"Không tìm thấy phiếu lấy hàng: {scan_code}.",
        }

    not_packed = [h.picking_no for h in headers if (h.pack_status or "") != "DONE"]
    if not_packed:
        return {
            "ok": False,
            "message": "Cửa hàng chưa đóng hàng đủ. Phiếu còn chờ đóng: " + ", ".join(not_packed),
        }

    picking_nos = [h.picking_no for h in headers]
    pack_headers = (
        db.query(PackHeader)
        .filter(PackHeader.picking_no.in_(picking_nos))
        .order_by(PackHeader.pack_type.asc(), PackHeader.picking_no.asc())
        .all()
    )

    if not pack_headers:
        return {
            "ok": False,
            "message": f"Nhóm phiếu {reference_code} đã có picking nhưng chưa có dữ liệu đóng hàng.",
        }

    store_id = headers[0].store_id or ""
    store_name = headers[0].store_name or ""
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

    do_nos = _do_nos_for_headers(db, headers)

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
        "scan_code": _clean_code(scan_code),
        "reference_code": reference_code,
        "picking_nos": picking_nos,
        "do_no": ", ".join(do_nos),
        "do_nos": do_nos,
        "total_do": len(do_nos),
        "store_id": store_id,
        "store_name": store_name,
        "trip_no": _join_distinct(getattr(h, "trip_no", "") for h in headers),
        "wave": _join_distinct(getattr(h, "wave", "") for h in headers),
        "khung_gio": _join_distinct(getattr(h, "khung_gio", "") for h in headers),
        "loai_giao": _join_distinct(getattr(h, "loai_giao", "") for h in headers),
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
        # Flow mới: tập kết theo cửa hàng/nhóm phiếu, không theo DO.
        key = (p.store_id or "", p.store_name or "")
        if key[0]:
            grouped[key].append(p)

    rows = []
    for (store_id, store_name), items in grouped.items():
        picking_nos = sorted({p.picking_no for p in items if p.picking_no})
        picking_headers = db.query(PickingHeader).filter(PickingHeader.picking_no.in_(picking_nos)).all()
        if not picking_headers:
            continue
        if any((h.pack_status or "") != "DONE" for h in picking_headers):
            continue
        if all((p.staging_status or "WAIT") == "DONE" for p in items):
            continue

        rows.append({
            "reference_code": picking_nos[0] if picking_nos else store_id,
            "picking_nos": picking_nos,
            "store_id": store_id,
            "store_name": store_name,
            "trip_no": _join_distinct(getattr(h, "trip_no", "") for h in picking_headers),
            "wave": _join_distinct(getattr(h, "wave", "") for h in picking_headers),
            "khung_gio": _join_distinct(getattr(h, "khung_gio", "") for h in picking_headers),
            "loai_giao": _join_distinct(getattr(h, "loai_giao", "") for h in picking_headers),
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

    reference_code = summary.get("reference_code") or _clean_code(scan_code)

    if summary.get("staging_status") == "DONE":
        return {
            "ok": False,
            "message": f"Nhóm phiếu {reference_code} đã xác nhận tập kết trước đó.",
        }

    now = now_vn()
    picking_nos = summary.get("picking_nos") or []

    pack_headers = db.query(PackHeader).filter(PackHeader.picking_no.in_(picking_nos)).all()
    for p in pack_headers:
        p.staging_status = "DONE"
        p.staging_confirm_user = user_name or ""
        p.staging_confirm_time = now
        p.staging_remark = remark or ""
        p.last_update = now

    do_nos = summary.get("do_nos") or []
    if do_nos:
        do_rows = db.query(DoDetail).filter(DoDetail.do_no.in_(do_nos)).all()
        for row in do_rows:
            row.status = "DONE"

    db.add(AuditLog(
        operation="STAGING_CONFIRM",
        reference_no=reference_code,
        pallet_id="",
        location_id="",
        sku="",
        barcode="",
        qty_before=int(summary.get("total_package") or 0),
        qty_after=int(summary.get("total_package") or 0),
        qty_change=0,
        user_name=user_name or "",
        remark=(
            f"Xác nhận tập kết nhóm phiếu {reference_code}: "
            f"store {summary.get('store_id', '')}, "
            f"tổng {summary.get('total_package', 0)} kiện, "
            f"chẵn {summary.get('even_package', 0)}, "
            f"lẻ {summary.get('odd_package', 0)}. "
            f"{remark or ''}"
        ).strip(),
    ))

    db.commit()

    summary = get_staging_summary(db, reference_code)
    summary["message"] = f"Đã xác nhận tập kết nhóm phiếu {reference_code}."
    return summary
