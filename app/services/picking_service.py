from datetime import datetime
from math import ceil

from sqlalchemy.orm import Session

from app.models.tables import (
    DoDetail,
    ProductMaster,
    SkuMaster,
    InventoryBalance,
    LocationMaster,
    PickingHeader,
    PickingDetail,
)


def ma_loai_phieu(pick_type: str) -> str:
    return "C" if pick_type == "CASE" else "L"


def ten_loai_phieu(pick_type: str) -> str:
    return "Hàng chẵn" if pick_type == "CASE" else "Hàng lẻ"


def tao_picking_no(do_no: str, pick_type: str) -> str:
    return f"{do_no}-{ma_loai_phieu(pick_type)}"


def tinh_so_tem_chuan(qty_do: int, pcb: int) -> int:
    if pcb <= 0:
        pcb = 1
    return ceil(qty_do / pcb)


def tinh_so_tem_tren_phieu(header, details) -> int:
    if header.pick_type == "CASE":
        return sum(d.label_qty or 0 for d in details)

    categories = set()
    for d in details:
        category = (d.category or "CHƯA PHÂN NGÀNH").strip()
        categories.add(category)

    return len(categories)


def lay_vi_tri_uu_tien(db: Session, sku: str):
    """
    Trả về vị trí pick tốt nhất cho SKU theo master location pick_index.

    Ghi chú vận hành:
    - pick_index nằm trong location_master do user import từ master data.
    - Khi tạo phiếu lấy hàng, hệ thống lưu snapshot pick_index vào picking_detail.
    - Khi in/xem phiếu, chỉ cần ORDER BY picking_detail.pick_index.
    - Nếu SKU chưa có tồn hoặc location chưa có master index, đẩy xuống cuối phiếu bằng 999999.
    """
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


def tao_phieu_lay_hang_theo_do(db: Session, do_no: str):
    do_no = do_no.strip()

    rows = db.query(DoDetail).filter(DoDetail.do_no == do_no).all()

    if not rows:
        raise ValueError("Không tìm thấy dữ liệu DO")

    old_headers = db.query(PickingHeader).filter(PickingHeader.do_no == do_no).all()

    for h in old_headers:
        db.query(PickingDetail).filter(
            PickingDetail.picking_id == h.picking_id
        ).delete()
        db.delete(h)

    db.flush()

    grouped = {}

    for r in rows:
        sku = (r.sku or "").strip().upper()

        if not sku:
            continue

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

        picking_no = tao_picking_no(r.do_no, pick_type)
        key = (r.do_no, r.store_id, pick_type)

        if key not in grouped:
            header = PickingHeader(
                picking_no=picking_no,
                do_no=r.do_no,
                store_id=r.store_id,
                store_name=r.store_name,
                pick_type=pick_type,
                status="WAIT_PICK",
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

        if pick_type == "CASE":
            label_qty = tinh_so_tem_chuan(r.qty_do, pcb)
        else:
            label_qty = 0

        detail = PickingDetail(
            picking_id=header.picking_id,
            do_no=r.do_no,
            store_id=r.store_id,
            store_name=r.store_name,
            sku=sku,
            barcode=r.barcode or "",
            product_name=r.product_name or "",
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

    return {
        "do_no": do_no,
        "so_phieu_lay_hang": len(grouped),
    }


def danh_sach_phieu_lay_hang(db: Session, print_status: str | None = None):
    query = db.query(PickingHeader)

    if print_status:
        query = query.filter(PickingHeader.print_status == print_status)

    return (
        query
        .order_by(PickingHeader.created_at.desc())
        .limit(300)
        .all()
    )


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
            PickingDetail.sku.asc(),
        )
        .all()
    )

    total_label_qty = tinh_so_tem_tren_phieu(header, details)

    return header, details, total_label_qty


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