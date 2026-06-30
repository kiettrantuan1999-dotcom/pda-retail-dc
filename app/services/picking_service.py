from datetime import datetime
from math import ceil
import re

from sqlalchemy.orm import Session
from sqlalchemy import text
from types import SimpleNamespace

from app.models.tables import (
    DoDetail,
    ProductMaster,
    SkuMaster,
    InventoryBalance,
    LocationMaster,
    PickingHeader,
    PickingDetail,
)


STORE_PICKING_DO_MARKER = "STORE_PICKING"


def ma_loai_phieu(pick_type: str) -> str:
    return "C" if (pick_type or "").upper() == "CASE" else "L"


def ten_loai_phieu(pick_type: str) -> str:
    return "Hàng chẵn" if (pick_type or "").upper() == "CASE" else "Hàng lẻ"


def _format_do_date_for_picking(value: str | None) -> str:
    """Chuẩn hóa ngày tạo DO thành DDMMYYYY để đưa vào mã phiếu."""
    text = str(value or "").strip()
    if not text:
        return datetime.now().strftime("%d%m%Y")

    # Excel đôi khi trả ngày dạng yyyy-mm-dd hh:mm:ss, dd/mm/yyyy, dd-mm-yyyy.
    for fmt in (
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%d%m%Y")
        except Exception:
            pass

    digits = re.sub(r"\D", "", text)
    if len(digits) >= 8:
        # yyyyMMdd -> ddMMyyyy
        if digits[:4].isdigit() and 1900 <= int(digits[:4]) <= 2100:
            return digits[6:8] + digits[4:6] + digits[0:4]
        # ddMMyyyy
        return digits[:8]

    return datetime.now().strftime("%d%m%Y")


def tao_picking_no_theo_store(store_id: str, pick_type: str, do_created_date: str | None = None) -> str:
    """Mã phiếu mới: Ngày tạo DO + Mã cửa hàng + Loại phiếu. Ví dụ: 30062026-0000002ACV-L."""
    store_id = (store_id or "").strip().upper()
    do_date = _format_do_date_for_picking(do_created_date)
    return f"{do_date}-{store_id}-{ma_loai_phieu(pick_type)}"


def tao_picking_no(do_no: str, pick_type: str) -> str:
    """Giữ hàm cũ để không vỡ import nơi khác, nhưng flow mới dùng theo store."""
    return f"{(do_no or '').strip().upper()}-{ma_loai_phieu(pick_type)}"


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def tinh_ty_le_tem(qty_do: int, pcb: int) -> float:
    """Tỷ lệ tem = SL / PCB. Chưa làm tròn ở cấp SKU line."""
    qty = max(_safe_int(qty_do, 0), 0)
    pcb = max(_safe_int(pcb, 1), 1)
    if qty <= 0:
        return 0.0
    return qty / pcb


def tinh_so_tem_chuan(qty_do: int, pcb: int, pick_type: str = "CASE") -> int:
    """Số tem nếu tính riêng 1 dòng. Giữ hàm cũ để tương thích."""
    return int(ceil(tinh_ty_le_tem(qty_do, pcb)))


def tinh_so_tem_tren_phieu(header, details) -> int:
    """
    Logic tem đúng theo vận hành:
    - Từng dòng chỉ tính tỷ lệ SL / PCB.
    - Tổng số tem của phiếu = CEIL(SUM(SL / PCB)).
    Không làm tròn từng SKU line để tránh bị đội số tem.
    """
    total_ratio = 0.0
    for d in details:
        total_ratio += tinh_ty_le_tem(
            getattr(d, "qty_pick", 0),
            getattr(d, "pcb", 1),
        )
    return int(ceil(total_ratio)) if total_ratio > 0 else 0


def dem_so_do_trong_phieu(details) -> int:
    return len({(d.do_no or "").strip() for d in details if (d.do_no or "").strip()})


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


def _meta_from_rows(rows) -> dict:
    return {
        "wave": _join_distinct(getattr(r, "wave", "") for r in rows),
        "khung_gio": _join_distinct(getattr(r, "khung_gio", "") for r in rows),
        "loai_giao": _join_distinct(getattr(r, "loai_giao", "") for r in rows),
        "trip_no": _join_distinct(getattr(r, "trip_no", "") for r in rows),
        "do_created_date": _join_distinct(getattr(r, "do_created_date", "") for r in rows),
    }


def lay_vi_tri_uu_tien(db: Session, sku: str):
    sku = (sku or "").strip().upper()

    if not sku:
        return "", 999999

    row = (
        db.query(InventoryBalance, LocationMaster)
        .outerjoin(
            LocationMaster,
            InventoryBalance.location_id == LocationMaster.location_id,
        )
        .filter(InventoryBalance.sku == sku)
        .filter(InventoryBalance.qty_onhand > 0)
        .order_by(
            LocationMaster.pick_index.asc().nullslast(),
            InventoryBalance.location_id.asc(),
        )
        .first()
    )

    if not row:
        return "", 999999

    inventory, location = row

    if location and location.pick_index is not None:
        return inventory.location_id, int(location.pick_index or 999999)

    return inventory.location_id, 999999


def _phan_loai_sku(db: Session, sku: str):
    sku_master = db.query(SkuMaster).filter(SkuMaster.sku == sku).first()
    product = db.query(ProductMaster).filter(ProductMaster.sku == sku).first()

    pick_type = "ODD"
    pcb = 1
    mhu = 1

    if sku_master:
        pick_type = (sku_master.sku_type or "ODD").upper()
        pcb = sku_master.pcb or 1
        mhu = sku_master.mhu or 1

    if pick_type not in ["CASE", "ODD"]:
        pick_type = "ODD"

    return pick_type, pcb, mhu, product


def _xoa_phieu_cua_hang_chua_xu_ly(db: Session, store_id: str):
    """
    Xóa phiếu store cũ chỉ khi chưa pick/pack.
    Không xóa phiếu đã in vẫn được phép vì in sai/import lại còn có thể tạo lại trước khi xử lý.
    """
    old_headers = (
        db.query(PickingHeader)
        .filter(PickingHeader.do_no == STORE_PICKING_DO_MARKER)
        .filter(PickingHeader.store_id == store_id)
        .all()
    )

    locked = [h.picking_no for h in old_headers if (h.status or "") not in ["WAIT_PICK"] or (h.pack_status or "") not in ["WAIT"]]
    if locked:
        raise ValueError("Không thể tạo lại phiếu cửa hàng đã xử lý/đã pack: " + ", ".join(locked))

    for h in old_headers:
        db.query(PickingDetail).filter(PickingDetail.picking_id == h.picking_id).delete()
        db.delete(h)

    db.flush()


def tao_phieu_lay_hang_theo_cua_hang(db: Session, store_id: str):
    """
    Flow mới: gom theo cửa hàng.

    1 cửa hàng -> tối đa 2 phiếu:
    - STORE-C: hàng chẵn
    - STORE-L: hàng lẻ

    Bên dưới PickingDetail vẫn giữ do_no từng dòng để pack/trừ tồn vẫn trace được nhiều DO.
    """
    store_id = (store_id or "").strip()
    if not store_id:
        raise ValueError("Thiếu mã cửa hàng")

    rows = db.query(DoDetail).filter(DoDetail.store_id == store_id).all()

    if not rows:
        raise ValueError("Không tìm thấy dữ liệu DO cho cửa hàng")

    _xoa_phieu_cua_hang_chua_xu_ly(db, store_id)

    meta = _meta_from_rows(rows)
    grouped = {}

    for r in rows:
        sku = (r.sku or "").strip().upper()
        if not sku:
            continue

        pick_type, pcb, mhu, product = _phan_loai_sku(db, sku)
        key = (r.store_id, pick_type)

        if key not in grouped:
            picking_no = tao_picking_no_theo_store(r.store_id, pick_type, meta.get("do_created_date"))
            header = PickingHeader(
                picking_no=picking_no,
                do_no=STORE_PICKING_DO_MARKER,
                store_id=r.store_id,
                store_name=r.store_name,
                wave=meta["wave"],
                khung_gio=meta["khung_gio"],
                loai_giao=meta["loai_giao"],
                trip_no=meta["trip_no"],
                pick_type=pick_type,
                status="WAIT_PICK",
                pack_status="WAIT",
                print_status="WAIT_PRINT",
                print_count=0,
                created_at=datetime.utcnow(),
                last_update=datetime.utcnow(),
            )
            db.add(header)
            db.flush()
            grouped[key] = header

        header = grouped[key]
        location_id, pick_index = lay_vi_tri_uu_tien(db, sku)
        label_qty = tinh_so_tem_chuan(r.qty_do, pcb, pick_type)

        detail = PickingDetail(
            picking_id=header.picking_id,
            do_no=r.do_no,
            store_id=r.store_id,
            store_name=r.store_name,
            sku=sku,
            barcode=(r.barcode or (product.barcode if product else "") or ""),
            product_name=(r.product_name or (product.product_name if product else "") or ""),
            uom=(r.uom or (product.uom if product else "") or ""),
            category=product.category if product else "CHƯA PHÂN NGÀNH",
            location_id=location_id,
            pick_index=pick_index,
            qty_pick=r.qty_do,
            pcb=pcb,
            mhu=mhu,
            pick_type=pick_type,
            label_qty=label_qty,
            status="WAIT_PICK",
            created_at=datetime.utcnow(),
        )
        db.add(detail)

    db.commit()

    so_do = len({r.do_no for r in rows if r.do_no})
    return {
        "store_id": store_id,
        "so_do": so_do,
        "so_phieu_lay_hang": len(grouped),
    }


def tao_phieu_lay_hang_theo_do(db: Session, do_no: str):
    """
    Tương thích ngược: nếu nơi cũ gọi theo DO thì tìm store của DO đó rồi gom lại theo cửa hàng.
    """
    do_no = (do_no or "").strip()
    rows = db.query(DoDetail).filter(DoDetail.do_no == do_no).all()
    if not rows:
        raise ValueError("Không tìm thấy dữ liệu DO")

    store_ids = sorted({r.store_id for r in rows if r.store_id})
    created = 0
    for store_id in store_ids:
        result = tao_phieu_lay_hang_theo_cua_hang(db, store_id)
        created += result["so_phieu_lay_hang"]

    return {
        "do_no": do_no,
        "so_phieu_lay_hang": created,
    }


def _table_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
        """),
        {"table_name": table_name},
    ).fetchall()
    return {r[0] for r in rows}


def _select_col(existing_cols: set[str], col: str, fallback: str = "''") -> str:
    if col in existing_cols:
        return f"h.{col} AS {col}"
    return f"{fallback} AS {col}"


def danh_sach_phieu_lay_hang(db: Session, print_status: str | None = None):
    """
    Safe list reader cho /picking.
    Không dùng db.query(PickingHeader) vì ORM sẽ SELECT tất cả cột trong model.
    Khi local DB chưa migrate đủ cột mới như wave/khung_gio/loai_giao/trip_no,
    ORM sẽ làm trang /picking bị 500.
    """
    cols = _table_columns(db, "picking_header")

    select_cols = [
        _select_col(cols, "picking_id", "NULL"),
        _select_col(cols, "picking_no", "''"),
        _select_col(cols, "do_no", "''"),
        _select_col(cols, "store_id", "''"),
        _select_col(cols, "store_name", "''"),
        _select_col(cols, "wave", "''"),
        _select_col(cols, "khung_gio", "''"),
        _select_col(cols, "loai_giao", "''"),
        _select_col(cols, "trip_no", "''"),
        _select_col(cols, "pick_type", "''"),
        _select_col(cols, "status", "''"),
        _select_col(cols, "pack_status", "''"),
        _select_col(cols, "print_status", "''"),
        _select_col(cols, "printed_by", "''"),
        _select_col(cols, "printed_at", "NULL"),
        _select_col(cols, "print_count", "0"),
        _select_col(cols, "created_at", "NULL"),
        _select_col(cols, "last_update", "NULL"),
        _select_col(cols, "carton_qty", "0"),
    ]

    where = ""
    params = {}
    if print_status:
        where = "WHERE h.print_status = :print_status"
        params["print_status"] = print_status

    sql = text(f"""
        SELECT {', '.join(select_cols)}
        FROM picking_header h
        {where}
        ORDER BY h.created_at DESC NULLS LAST, h.picking_id DESC
        LIMIT 300
    """)

    result = []
    for row in db.execute(sql, params).mappings().all():
        result.append(SimpleNamespace(**dict(row)))
    return result


def chi_tiet_phieu_lay_hang(db: Session, picking_id: int):
    header = (
        db.query(PickingHeader)
        .filter(PickingHeader.picking_id == picking_id)
        .first()
    )

    if not header:
        raise ValueError("Không tìm thấy phiếu lấy hàng")

    details = (
        db.query(PickingDetail)
        .filter(PickingDetail.picking_id == picking_id)
        .order_by(
            PickingDetail.pick_index.asc(),
            PickingDetail.location_id.asc(),
            PickingDetail.do_no.asc(),
            PickingDetail.sku.asc(),
        )
        .all()
    )

    total_label_qty = tinh_so_tem_tren_phieu(header, details)

    return header, details, total_label_qty


def _detail_to_dict(d):
    """Convert SQLAlchemy detail row to dict for template-safe rendering."""
    qty_pick = _safe_int(getattr(d, "qty_pick", 0), 0)
    pcb = max(_safe_int(getattr(d, "pcb", 1), 1), 1)
    pick_type = (getattr(d, "pick_type", "") or "ODD").upper()
    label_qty = _safe_int(getattr(d, "label_qty", 0), 0)
    if label_qty <= 0:
        label_qty = tinh_so_tem_chuan(qty_pick, pcb, pick_type)

    label_ratio = tinh_ty_le_tem(qty_pick, pcb)

    return {
        "picking_detail_id": getattr(d, "picking_detail_id", None),
        "do_no": getattr(d, "do_no", "") or "",
        "store_id": getattr(d, "store_id", "") or "",
        "store_name": getattr(d, "store_name", "") or "",
        "sku": getattr(d, "sku", "") or "",
        "barcode": getattr(d, "barcode", "") or "",
        "product_name": getattr(d, "product_name", "") or "",
        "uom": getattr(d, "uom", "") or "",
        "category": getattr(d, "category", "") or "",
        "location_id": getattr(d, "location_id", "") or "",
        "pick_index": _safe_int(getattr(d, "pick_index", 999999), 999999),
        "qty_pick": qty_pick,
        "pcb": pcb,
        "mhu": _safe_int(getattr(d, "mhu", 1), 1),
        "pick_type": pick_type,
        "label_qty": label_qty,
        "label_ratio": round(label_ratio, 2),
        "status": getattr(d, "status", "") or "",
        "pack_status": getattr(d, "pack_status", "") or "",
    }


def tong_hop_dong_pick(details):
    """
    Trả dữ liệu cho màn hình chi tiết.
    Hiện tại vẫn giữ từng SKU line/DO line để không mất trace sang Pack.
    """
    return [_detail_to_dict(d) for d in details]


def thong_ke_phieu(details):
    rows = [_detail_to_dict(d) for d in details]
    return {
        "so_do": len({r["do_no"] for r in rows if r["do_no"]}),
        "so_sku": len({r["sku"] for r in rows if r["sku"]}),
        "so_line": len(rows),
        "tong_sl": sum(r["qty_pick"] for r in rows),
        "tong_tem": int(ceil(sum(tinh_ty_le_tem(r["qty_pick"], r["pcb"]) for r in rows))),
    }


def danh_dau_da_in(db: Session, picking_id: int, user_name: str = "developer"):
    header = (
        db.query(PickingHeader)
        .filter(PickingHeader.picking_id == picking_id)
        .first()
    )

    if not header:
        raise ValueError("Không tìm thấy phiếu lấy hàng")

    header.print_status = "PRINTED"
    header.printed_by = user_name
    header.printed_at = datetime.utcnow()
    header.print_count = (header.print_count or 0) + 1
    header.last_update = datetime.utcnow()

    db.commit()
    db.refresh(header)

    return {
        "picking_id": header.picking_id,
        "picking_no": header.picking_no,
        "print_status": header.print_status,
        "print_count": header.print_count,
    }


# =====================================================
# Sprint 31 - Safe print reader
# Mục tiêu: trang /picking/{id}/print không phụ thuộc ORM SELECT toàn bộ cột.
# Lý do: một số DB local đã tạo bảng trước khi thêm cột barcode/uom/pcb/label_qty,
# SQLAlchemy ORM sẽ lỗi 500 nếu model có cột nhưng DB thật chưa có.
# Hàm dưới đây đọc bằng raw SQL + inspect schema, thiếu cột nào thì tự fallback.
# =====================================================
from types import SimpleNamespace
from sqlalchemy import inspect, text


def _cols(db: Session, table_name: str) -> set[str]:
    try:
        return {c["name"] for c in inspect(db.bind).get_columns(table_name)}
    except Exception:
        return set()


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


def _q(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _select_expr(table_alias: str, cols: set[str], col: str, default_sql: str) -> str:
    if col in cols:
        return f"{table_alias}.{_q(col)} AS {_q(col)}"
    return f"{default_sql} AS {_q(col)}"


def _row_get(row, key, default=None):
    try:
        return row._mapping.get(key, default)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


def _line_label_ratio(qty, pcb) -> float:
    return tinh_ty_le_tem(qty, pcb)


def _line_label_qty(qty, pcb, pick_type: str) -> int:
    # Giữ hàm cũ để tương thích; tổng phiếu sẽ dùng CEIL(SUM ratio)).
    return int(ceil(_line_label_ratio(qty, pcb)))


def chi_tiet_phieu_lay_hang_print_safe(db: Session, picking_id: int):
    ph_cols = _cols(db, "picking_header")
    pd_cols = _cols(db, "picking_detail")
    pm_cols = _cols(db, "product_master")
    sm_cols = _cols(db, "sku_master")
    dd_cols = _cols(db, "do_detail")

    # Header: chỉ select những cột chắc chắn tồn tại, thiếu thì default.
    header_fields = [
        ("picking_id", "NULL"),
        ("picking_no", "''"),
        ("do_no", "''"),
        ("store_id", "''"),
        ("store_name", "''"),
        ("wave", "''"),
        ("khung_gio", "''"),
        ("loai_giao", "''"),
        ("trip_no", "''"),
        ("pick_type", "'ODD'"),
        ("status", "''"),
        ("pack_status", "''"),
        ("print_status", "'WAIT_PRINT'"),
        ("printed_by", "''"),
        ("printed_at", "NULL"),
        ("print_count", "0"),
        ("created_at", "NULL"),
        ("last_update", "NULL"),
    ]
    header_select = ", ".join(_select_expr("h", ph_cols, c, d) for c, d in header_fields)
    h_sql = text(f"SELECT {header_select} FROM picking_header h WHERE h.picking_id = :picking_id")
    h_row = db.execute(h_sql, {"picking_id": picking_id}).first()
    if not h_row:
        raise ValueError("Không tìm thấy phiếu lấy hàng")

    h_map = dict(h_row._mapping)
    header = _ns(**h_map)

    # Detail: đọc raw + fallback barcode/ĐVT/product/PCB từ do_detail/product_master/sku_master.
    joins = []
    if pm_cols:
        joins.append("LEFT JOIN product_master pm ON UPPER(TRIM(pm.sku)) = UPPER(TRIM(d.sku))")
    if sm_cols:
        joins.append("LEFT JOIN sku_master sm ON UPPER(TRIM(sm.sku)) = UPPER(TRIM(d.sku))")
    if dd_cols:
        joins.append("LEFT JOIN do_detail dd ON dd.do_no = d.do_no AND dd.store_id = d.store_id AND UPPER(TRIM(dd.sku)) = UPPER(TRIM(d.sku))")

    def dcol(col, default):
        return _select_expr("d", pd_cols, col, default)

    barcode_expr = "''"
    barcode_parts = []
    if "barcode" in pd_cols:
        barcode_parts.append("NULLIF(d.barcode, '')")
    if "barcode" in dd_cols:
        barcode_parts.append("NULLIF(dd.barcode, '')")
    if "barcode" in pm_cols:
        barcode_parts.append("NULLIF(pm.barcode, '')")
    if barcode_parts:
        barcode_expr = "COALESCE(" + ", ".join(barcode_parts) + ", '')"

    uom_expr = "''"
    uom_parts = []
    if "uom" in pd_cols:
        uom_parts.append("NULLIF(d.uom, '')")
    if "uom" in dd_cols:
        uom_parts.append("NULLIF(dd.uom, '')")  # Excel cột ĐVT được map vào do_detail.uom
    if "uom" in pm_cols:
        uom_parts.append("NULLIF(pm.uom, '')")
    if uom_parts:
        uom_expr = "COALESCE(" + ", ".join(uom_parts) + ", '')"

    product_expr = "''"
    product_parts = []
    if "product_name" in pd_cols:
        product_parts.append("NULLIF(d.product_name, '')")
    if "product_name" in dd_cols:
        product_parts.append("NULLIF(dd.product_name, '')")
    if "product_name" in pm_cols:
        product_parts.append("NULLIF(pm.product_name, '')")
    if product_parts:
        product_expr = "COALESCE(" + ", ".join(product_parts) + ", '')"

    category_expr = "''"
    category_parts = []
    if "category" in pd_cols:
        category_parts.append("NULLIF(d.category, '')")
    if "category" in pm_cols:
        category_parts.append("NULLIF(pm.category, '')")
    if category_parts:
        category_expr = "COALESCE(" + ", ".join(category_parts) + ", 'CHƯA PHÂN NGÀNH')"

    pcb_expr = "1"
    pcb_parts = []
    if "pcb" in pd_cols:
        pcb_parts.append("NULLIF(d.pcb, 0)")
    if "pcb" in sm_cols:
        pcb_parts.append("NULLIF(sm.pcb, 0)")
    if "pcb" in pm_cols:
        pcb_parts.append("NULLIF(pm.pcb, 0)")
    if pcb_parts:
        pcb_expr = "COALESCE(" + ", ".join(pcb_parts) + ", 1)"

    mhu_expr = "1"
    mhu_parts = []
    if "mhu" in pd_cols:
        mhu_parts.append("NULLIF(d.mhu, 0)")
    if "mhu" in sm_cols:
        mhu_parts.append("NULLIF(sm.mhu, 0)")
    if mhu_parts:
        mhu_expr = "COALESCE(" + ", ".join(mhu_parts) + ", 1)"

    select_parts = [
        dcol("picking_detail_id", "NULL"),
        dcol("picking_id", ":picking_id"),
        dcol("do_no", "''"),
        dcol("store_id", "''"),
        dcol("store_name", "''"),
        dcol("sku", "''"),
        f"{barcode_expr} AS barcode",
        f"{product_expr} AS product_name",
        f"{uom_expr} AS uom",
        f"{category_expr} AS category",
        dcol("location_id", "''"),
        dcol("pick_index", "999999"),
        dcol("qty_pick", "0"),
        f"{pcb_expr} AS pcb",
        f"{mhu_expr} AS mhu",
        dcol("pick_type", f"'{getattr(header, 'pick_type', 'ODD') or 'ODD'}'"),
        dcol("label_qty", "0"),
        dcol("status", "'WAIT_PICK'"),
        dcol("pack_status", "'WAIT'"),
    ]
    order_parts = []
    if "pick_index" in pd_cols:
        order_parts.append("d.pick_index ASC")
    if "location_id" in pd_cols:
        order_parts.append("d.location_id ASC")
    if "do_no" in pd_cols:
        order_parts.append("d.do_no ASC")
    if "sku" in pd_cols:
        order_parts.append("d.sku ASC")
    order_sql = ", ".join(order_parts) or "1"

    d_sql = text(f"""
        SELECT {', '.join(select_parts)}
        FROM picking_detail d
        {' '.join(joins)}
        WHERE d.picking_id = :picking_id
        ORDER BY {order_sql}
    """)
    rows = db.execute(d_sql, {"picking_id": picking_id}).fetchall()

    # Gộp dòng in theo SKU để picker không thấy duplicate SKU khi cùng cửa hàng có nhiều DO.
    # PickingDetail vẫn giữ dòng gốc theo DO để Pack còn trace; chỉ màn detail/print gom lại.
    grouped = {}
    for row in rows:
        m = dict(row._mapping)
        sku = (m.get("sku") or "").strip().upper()
        if not sku:
            continue
        qty = _safe_int(m.get("qty_pick"), 0)
        pcb = max(_safe_int(m.get("pcb"), 1), 1)
        pick_type = (m.get("pick_type") or getattr(header, "pick_type", "ODD") or "ODD").upper()
        ratio = _line_label_ratio(qty, pcb)

        key = sku
        if key not in grouped:
            m["sku"] = sku
            m["qty_pick"] = 0
            m["pcb"] = pcb
            m["mhu"] = max(_safe_int(m.get("mhu"), 1), 1)
            m["pick_type"] = pick_type
            m["_label_ratio_sum"] = 0.0
            m["_do_set"] = set()
            grouped[key] = m

        g = grouped[key]
        g["qty_pick"] += qty
        g["_label_ratio_sum"] += ratio
        if m.get("do_no"):
            g["_do_set"].add(m.get("do_no"))

        # Nếu dòng đầu thiếu thông tin, lấy fallback từ dòng sau.
        for col in ["barcode", "product_name", "uom", "category", "location_id"]:
            if not g.get(col) and m.get(col):
                g[col] = m.get(col)
        g["pick_index"] = min(_safe_int(g.get("pick_index"), 999999), _safe_int(m.get("pick_index"), 999999))

    details = []
    total_ratio = 0.0
    for m in grouped.values():
        ratio = float(m.pop("_label_ratio_sum", 0.0))
        do_set = m.pop("_do_set", set())
        m["do_no"] = ", ".join(sorted(do_set)) if do_set else (m.get("do_no") or "")
        m["label_ratio"] = round(ratio, 2)
        m["label_qty"] = int(ceil(ratio)) if ratio > 0 else 0
        total_ratio += ratio
        details.append(_ns(**m))

    details.sort(key=lambda x: (getattr(x, "pick_index", 999999), getattr(x, "location_id", "") or "", getattr(x, "sku", "") or ""))
    total_label_qty = int(ceil(total_ratio)) if total_ratio > 0 else 0

    return header, details, total_label_qty


def danh_dau_da_in_safe(db: Session, picking_id: int, user_name: str = "developer"):
    """Update trạng thái in bằng raw SQL, chỉ update cột đang tồn tại."""
    ph_cols = _cols(db, "picking_header")
    sets = []
    params = {"picking_id": picking_id, "user_name": user_name}
    if "print_status" in ph_cols:
        sets.append("print_status = 'PRINTED'")
    if "printed_by" in ph_cols:
        sets.append("printed_by = :user_name")
    if "printed_at" in ph_cols:
        sets.append("printed_at = CURRENT_TIMESTAMP")
    if "print_count" in ph_cols:
        sets.append("print_count = COALESCE(print_count, 0) + 1")
    if "last_update" in ph_cols:
        sets.append("last_update = CURRENT_TIMESTAMP")
    if not sets:
        return
    db.execute(text(f"UPDATE picking_header SET {', '.join(sets)} WHERE picking_id = :picking_id"), params)
    db.commit()



def chuan_hoa_ma_phieu_theo_ngay_do(db: Session, store_ids: list[str] | None = None) -> int:
    """
    Chuẩn hóa mã phiếu Picking theo format: DDMMYYYY-MA_CUA_HANG-C/L.
    Ngày lấy từ do_detail.do_created_date theo cửa hàng. Nếu thiếu thì fallback created_at của phiếu.
    """
    filters = "WHERE h.do_no = :marker"
    params = {"marker": STORE_PICKING_DO_MARKER}

    if store_ids:
        clean_store_ids = [str(x).strip() for x in store_ids if str(x).strip()]
        if clean_store_ids:
            filters += " AND h.store_id = ANY(:store_ids)"
            params["store_ids"] = clean_store_ids

    rows = db.execute(text(f"""
        SELECT
            h.picking_id,
            h.store_id,
            h.pick_type,
            h.created_at,
            MIN(NULLIF(d.do_created_date, '')) AS do_created_date
        FROM picking_header h
        LEFT JOIN do_detail d
            ON d.store_id = h.store_id
        {filters}
        GROUP BY h.picking_id, h.store_id, h.pick_type, h.created_at
    """), params).mappings().all()

    updated = 0
    for r in rows:
        store_id = (r.get("store_id") or "").strip().upper()
        if not store_id:
            continue

        date_source = r.get("do_created_date")
        if not date_source and r.get("created_at"):
            try:
                date_source = r.get("created_at").strftime("%d/%m/%Y")
            except Exception:
                date_source = str(r.get("created_at"))

        new_no = tao_picking_no_theo_store(store_id, r.get("pick_type") or "ODD", date_source)
        db.execute(
            text("UPDATE picking_header SET picking_no = :new_no WHERE picking_id = :picking_id"),
            {"new_no": new_no, "picking_id": r.get("picking_id")},
        )
        updated += 1

    db.flush()
    return updated
