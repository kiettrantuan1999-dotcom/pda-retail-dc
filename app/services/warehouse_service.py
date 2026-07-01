from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.tables import (
    ProductMaster,
    SkuMaster,
    PoDetail,
    InboundQueue,
    PalletHeader,
    PalletDetail,
    GrLog,
    InventoryBalance,
    LocationMaster,
    CategoryAisleMaster,
    SkuLocationOverride,
    PutawayLog,
    MasterDataIssue,
    AuditLog,
)

print("WAREHOUSE SERVICE LOADED:", __file__)


def _clean_lookup_text(value: str) -> str:
    """Chuẩn hóa text nhập/scan để tránh lệch do khoảng trắng, chữ thường/hoa."""
    return str(value or "").strip()


def _po_filter_value(value: str) -> str:
    return _clean_lookup_text(value).upper()


def _find_po_detail_rows(db: Session, po_no: str):
    clean_po = _clean_lookup_text(po_no)
    if not clean_po:
        return []

    rows = (
        db.query(PoDetail)
        .filter(PoDetail.po_no == clean_po)
        .order_by(PoDetail.sku.asc())
        .all()
    )
    if rows:
        return rows

    # Fallback cho case file upload/scanner lệch khoảng trắng hoặc chữ hoa/thường.
    return (
        db.query(PoDetail)
        .filter(func.upper(func.trim(PoDetail.po_no)) == _po_filter_value(clean_po))
        .order_by(PoDetail.sku.asc())
        .all()
    )

def product_by_barcode(db: Session, barcode: str):
    barcode = barcode.strip()
    return db.query(ProductMaster).filter(ProductMaster.barcode == barcode).first()



def _unknown_sku_from_barcode(barcode: str) -> str:
    clean = str(barcode or "").strip()
    return (f"UNKNOWN-{clean}" if clean else "UNKNOWN-BARCODE")[:100]


def _product_payload_from_master(db: Session, barcode: str):
    """Lấy thông tin sản phẩm theo barcode.

    Rule vận hành:
    - Chẵn/lẻ lấy theo master data, không suy luận bằng SL % PCB.
    - Barcode chưa có master vẫn được GR và Put Away vào vị trí thực tế.
    """
    product = product_by_barcode(db, barcode)

    if not product:
        return {
            "sku": _unknown_sku_from_barcode(barcode),
            "barcode": barcode,
            "product_name": "Hàng chưa có master",
            "uom": "EA",
            "category": "CHUA_CO_MASTER",
            "pcb": 1,
            "sku_type": "UNKNOWN",
            "putaway_type": "UNKNOWN",
            "putaway_type_label": "CHƯA CÓ MASTER",
            "is_unknown_master": True,
            "warning": "Barcode chưa có trong Product Master. Hệ thống vẫn cho GR/Put Away vào vị trí thực tế; vui lòng bổ sung master sau.",
        }

    sku_master = db.query(SkuMaster).filter(SkuMaster.sku == product.sku).first()
    pcb = int((sku_master.pcb if sku_master and sku_master.pcb else 1) or 1)
    sku_type = sku_master.sku_type if sku_master else "UNKNOWN"
    putaway_type = _putaway_type_from_master(sku_type)

    return {
        "sku": product.sku,
        "barcode": product.barcode,
        "product_name": product.product_name or "",
        "uom": product.uom or "EA",
        "category": product.category or "",
        "pcb": pcb,
        "sku_type": sku_type or "UNKNOWN",
        "putaway_type": putaway_type,
        "putaway_type_label": _putaway_type_label(putaway_type),
        "is_unknown_master": False,
        "warning": "" if putaway_type != "UNKNOWN" else "SKU chưa có loại chẵn/lẻ trong Sku Master. Hệ thống không tự suy luận theo số lượng.",
    }


def _po_line_for_barcode(db: Session, po_no: str, barcode: str):
    po_no = _clean_lookup_text(po_no)
    barcode = _clean_lookup_text(barcode)
    if not po_no or not barcode:
        return None

    row = (
        db.query(PoDetail)
        .filter(PoDetail.po_no == po_no, PoDetail.barcode == barcode)
        .first()
    )
    if row:
        return row

    return (
        db.query(PoDetail)
        .filter(
            func.upper(func.trim(PoDetail.po_no)) == _po_filter_value(po_no),
            func.trim(PoDetail.barcode) == barcode,
        )
        .first()
    )

def _calc_po_line_received(db: Session, po_no: str, sku: str, barcode: str) -> int:
    po_no = _clean_lookup_text(po_no)
    sku = _clean_lookup_text(sku)
    barcode = _clean_lookup_text(barcode)
    rows = (
        db.query(InboundQueue)
        .filter(
            func.upper(func.trim(InboundQueue.po_no)) == _po_filter_value(po_no),
            InboundQueue.sku == sku,
            InboundQueue.barcode == barcode,
        )
        .all()
    )
    return sum(int(r.qty_gr or 0) for r in rows)


def _receipt_status(qty_total: int, qty_order: int) -> str:
    qty_total = int(qty_total or 0)
    qty_order = int(qty_order or 0)
    if qty_total > qty_order:
        return "DƯ"
    if qty_total == qty_order and qty_order > 0:
        return "ĐỦ"
    return "THIẾU"


def get_product_scan_info(db: Session, barcode: str, po_no: str = ""):
    barcode = barcode.strip()

    if not barcode:
        raise ValueError("Vui lòng scan barcode sản phẩm")

    product_info = _product_payload_from_master(db, barcode)

    # Nếu đang scan trong GR theo PO, barcode bắt buộc phải nằm trong PO detail đã upload.
    # Đây là kiểm soát chứng từ trung tâm đặt hàng, tránh nhập nhầm SKU ngoài PO.
    if po_no:
        po_line = _po_line_for_barcode(db, po_no, barcode)
        if not po_line:
            raise ValueError(f"Barcode {barcode} không có trong PO {po_no}. Vui lòng kiểm tra file PO detail hoặc scan lại.")

        product_info["sku"] = po_line.sku
        product_info["barcode"] = po_line.barcode
        product_info["product_name"] = po_line.product_name or product_info.get("product_name") or ""
        product_info["qty_order"] = int(po_line.qty_order or 0)
        product_info["qty_received"] = _calc_po_line_received(db, po_no, po_line.sku, po_line.barcode)
        product_info["receipt_status"] = _receipt_status(product_info["qty_received"], product_info["qty_order"])

    return product_info


def get_gr_po_detail_summary(db: Session, po_no: str):
    po_no = (po_no or "").strip()
    if not po_no:
        raise ValueError("Vui lòng scan/nhập PO")

    po_rows = _find_po_detail_rows(db, po_no)

    if not po_rows:
        raise ValueError(f"PO {po_no} chưa có trong PO detail. Vui lòng upload file PO detail trước khi GR.")

    rows = []
    total_order = total_received = 0

    for r in po_rows:
        product_info = _product_payload_from_master(db, r.barcode)
        pcb = int(product_info.get("pcb") or 1)
        qty_total = _calc_po_line_received(db, po_no, r.sku, r.barcode)
        carton_qty = qty_total // pcb if pcb > 0 else 0
        loose_qty = qty_total % pcb if pcb > 0 else qty_total
        qty_order = int(r.qty_order or 0)
        status = _receipt_status(qty_total, qty_order)
        note = ""
        if status == "DƯ":
            note = f"Dư {qty_total - qty_order}"
        elif status == "THIẾU":
            note = f"Thiếu {qty_order - qty_total}"
        else:
            note = "Đã nhận đủ"

        rows.append({
            "sku": r.sku,
            "barcode": r.barcode,
            "product_name": r.product_name or product_info.get("product_name") or "",
            "qty_order": qty_order,
            "pcb": pcb,
            "carton_qty": carton_qty,
            "loose_qty": loose_qty,
            "qty_total": qty_total,
            "status": status,
            "note": note,
        })
        total_order += qty_order
        total_received += qty_total

    return {
        "po_no": po_no,
        "total_sku": len(rows),
        "total_order": total_order,
        "total_received": total_received,
        "status": _receipt_status(total_received, total_order),
        "rows": rows,
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
    """GR theo mô hình vận hành mới: 1 PO = N PA, 1 PA = N SKU.

    Mỗi lần confirm là thêm/cộng một SKU vào PA. PA không còn bị khóa sau dòng SKU đầu tiên.
    Nếu cùng PA + cùng SKU/barcode được scan lại khi chưa Put Away thì cộng thêm số lượng vào dòng hiện có.
    """
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

    po_line = _po_line_for_barcode(db, po_no, barcode)
    if not po_line:
        raise ValueError(f"Barcode {barcode} không có trong PO {po_no}. Vui lòng kiểm tra file PO detail hoặc scan lại.")

    product_info = _product_payload_from_master(db, barcode)
    sku = po_line.sku
    product_name = po_line.product_name or product_info.get("product_name") or ""
    is_unknown_master = bool(product_info.get("is_unknown_master"))
    master_pcb = int(product_info.get("pcb") or 1)
    pcb = int(pcb or master_pcb or 1)

    if pcb <= 0:
        raise ValueError("PCB phải lớn hơn 0")

    qty_base = carton_qty * pcb + loose_qty

    # Backward compatible: nếu form cũ còn gửi qty_gr thì vẫn nhận, nhưng ưu tiên công thức mới.
    if qty_base <= 0 and qty_gr is not None:
        qty_base = int(qty_gr or 0)

    qty_total = qty_base + qty_promo

    if qty_total <= 0:
        raise ValueError("Tổng số lượng nhập phải lớn hơn 0")

    now = datetime.utcnow()

    if is_unknown_master:
        db.add(MasterDataIssue(
            issue_type="BARCODE_NOT_IN_PRODUCT_MASTER",
            sku=sku,
            barcode=barcode,
            pallet_id=pallet_id,
            location_id="",
            source_module="GR",
            source_ref_id=po_no,
            created_by=user_name,
            note="GR barcode chưa có trong product_master; hệ thống tạo SKU tạm để không chặn vận hành.",
        ))

    # 1 PA chỉ thuộc 1 PO. Nếu scan PA đã thuộc PO khác thì chặn để tránh lẫn chứng từ.
    pallet_header = db.query(PalletHeader).filter(PalletHeader.pallet_id == pallet_id).first()
    if pallet_header and pallet_header.po_no != po_no:
        raise ValueError(f"PA {pallet_id} đã thuộc PO {pallet_header.po_no}, không thể GR vào PO {po_no}")

    if not pallet_header:
        pallet_header = PalletHeader(
            pallet_id=pallet_id,
            po_no=po_no,
            status="DRAFT",
            created_by=user_name,
            created_at=now,
            last_update=now,
        )
        db.add(pallet_header)
    else:
        header_status = (pallet_header.status or "").upper()
        if header_status in ["WAIT_PUTAWAY", "PARTIAL", "DONE"]:
            raise ValueError("PA đã hoàn tất hoặc đã Put Away, không được thêm SKU. Vui lòng tạo PA mới hoặc nhờ quản lý kiểm tra.")
        pallet_header.status = "DRAFT"
        pallet_header.last_update = now

    # Dòng task theo SKU trong cùng PA. Cho phép 1 PA có nhiều SKU.
    queue = (
        db.query(InboundQueue)
        .filter(
            InboundQueue.po_no == po_no,
            InboundQueue.pallet_id == pallet_id,
            InboundQueue.sku == sku,
            InboundQueue.barcode == barcode,
        )
        .first()
    )

    if queue and (queue.flow_status or "").upper() not in ["DRAFT"]:
        raise ValueError("Dòng SKU này không còn ở trạng thái DRAFT, không được GR cộng thêm. Vui lòng tạo PA mới hoặc nhờ quản lý kiểm tra.")

    old_qty = int(queue.qty_gr or 0) if queue else 0

    if queue:
        queue.qty_gr = old_qty + qty_total
        queue.qty_remain_putaway = int(queue.qty_remain_putaway or 0) + qty_total
        queue.flow_status = "DRAFT"
        queue.last_update = now
    else:
        queue = InboundQueue(
            po_no=po_no,
            pallet_id=pallet_id,
            barcode=barcode,
            sku=sku,
            qty_gr=qty_total,
            qty_putaway=0,
            qty_remain_putaway=qty_total,
            flow_status="DRAFT",
            last_update=now,
        )
        db.add(queue)

    pallet_detail = (
        db.query(PalletDetail)
        .filter(
            PalletDetail.pallet_id == pallet_id,
            PalletDetail.sku == sku,
            PalletDetail.barcode == barcode,
        )
        .first()
    )

    if pallet_detail:
        pallet_detail.qty_gr = int(pallet_detail.qty_gr or 0) + qty_total
        pallet_detail.qty_remain_putaway = int(pallet_detail.qty_remain_putaway or 0) + qty_total
        pallet_detail.status = "DRAFT"
        pallet_detail.last_update = now
    else:
        pallet_detail = PalletDetail(
            pallet_id=pallet_id,
            po_no=po_no,
            barcode=barcode,
            sku=sku,
            qty_gr=qty_total,
            qty_putaway=0,
            qty_remain_putaway=qty_total,
            status="DRAFT",
            created_at=now,
            last_update=now,
        )
        db.add(pallet_detail)

    log = GrLog(
        po_no=po_no,
        pallet_id=pallet_id,
        barcode=barcode,
        sku=sku,
        qty_gr=qty_total,
        user_name=user_name,
    )

    # Đồng bộ số lượng đã nhận về PO detail để màn hình PO đối chiếu nhanh và import sau không mất trạng thái.
    po_line.qty_received = _calc_po_line_received(db, po_no, sku, barcode) + qty_total
    po_line.qty_remaining = max(int(po_line.qty_order or 0) - int(po_line.qty_received or 0), 0)
    po_line.status = _receipt_status(int(po_line.qty_received or 0), int(po_line.qty_order or 0))
    po_line.last_update = now

    db.add(log)
    db.add(AuditLog(
        operation="GR",
        reference_no=po_no,
        pallet_id=pallet_id,
        location_id="",
        sku=sku,
        barcode=barcode,
        qty_before=old_qty,
        qty_after=old_qty + qty_total,
        qty_change=qty_total,
        qty_regular=qty_base,
        qty_promo=qty_promo,
        qty_total=qty_total,
        user_name=user_name,
        remark=(
            f"Nhận hàng mixed PA: PCB={pcb}, thùng chẵn={carton_qty}, "
            f"kiện lẻ={loose_qty}, hàng thường={qty_base}, khuyến mãi={qty_promo}, "
            f"tổng dòng={qty_total}, PA={pallet_id}"
        ),
    ))
    db.commit()
    db.refresh(queue)

    pallet_summary = get_gr_pallet_summary(db, po_no, pallet_id)

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
        "product_name": product_name,
        "putaway_type": product_info.get("putaway_type") or "UNKNOWN",
        "putaway_type_label": product_info.get("putaway_type_label") or "CHƯA XÁC ĐỊNH",
        "is_unknown_master": is_unknown_master,
        "warning": product_info.get("warning") or "",
        "qty_total": qty_total,
        "line_total_after": queue.qty_gr,
        "pallet_total_sku": pallet_summary["total_sku"],
        "pallet_total_qty": pallet_summary["total_qty"],
        "qty_remain_putaway": queue.qty_remain_putaway,
        "flow_status": queue.flow_status,
    }


def get_gr_pallet_summary(db: Session, po_no: str, pallet_id: str):
    rows = (
        db.query(InboundQueue)
        .filter(InboundQueue.po_no == po_no, InboundQueue.pallet_id == pallet_id)
        .all()
    )
    return {
        "total_sku": len(rows),
        "total_qty": sum(int(r.qty_gr or 0) for r in rows),
        "total_remain": sum(int(r.qty_remain_putaway or 0) for r in rows),
    }


def complete_gr_pallet(
    db: Session,
    po_no: str,
    pallet_id: str,
    user_name: str = "developer",
):
    """Hoàn tất PA sau khi đã scan đủ SKU.

    Chuyển toàn bộ dòng SKU của PA từ DRAFT sang WAIT_PUTAWAY.
    Chỉ sau bước này PA mới xuất hiện ở Put Away.
    """
    po_no = (po_no or "").strip()
    pallet_id = (pallet_id or "").strip().upper()

    if not po_no:
        raise ValueError("Vui lòng nhập PO trước khi hoàn tất PA")

    if not pallet_id:
        raise ValueError("Vui lòng nhập PA trước khi hoàn tất PA")

    queues = (
        db.query(InboundQueue)
        .filter(
            InboundQueue.po_no == po_no,
            InboundQueue.pallet_id == pallet_id,
        )
        .order_by(InboundQueue.queue_id.asc())
        .all()
    )

    if not queues:
        raise ValueError("PA chưa có SKU nào, không thể hoàn tất")

    statuses = {(q.flow_status or "").upper() for q in queues}
    if "DONE" in statuses or "PARTIAL" in statuses:
        raise ValueError("PA đã Put Away một phần/toàn bộ, không thể hoàn tất lại")
    if statuses and statuses.issubset({"WAIT_PUTAWAY"}):
        raise ValueError("PA này đã được hoàn tất trước đó và đang chờ Put Away")

    invalid_qty_rows = [q for q in queues if int(q.qty_gr or 0) <= 0]
    if invalid_qty_rows:
        raise ValueError("Có SKU chưa có số lượng hợp lệ, không thể hoàn tất PA")

    now = datetime.utcnow()
    changed = 0

    for q in queues:
        status = (q.flow_status or "").upper()
        if status == "DRAFT":
            q.flow_status = "WAIT_PUTAWAY"
            q.last_update = now
            changed += 1
        elif status == "WAIT_PUTAWAY":
            # Idempotent: PA đã hoàn tất trước đó.
            q.last_update = now
        else:
            raise ValueError(f"Dòng SKU {q.sku} đang ở trạng thái {q.flow_status}, không thể hoàn tất PA")

    detail_rows = (
        db.query(PalletDetail)
        .filter(
            PalletDetail.po_no == po_no,
            PalletDetail.pallet_id == pallet_id,
        )
        .all()
    )

    for d in detail_rows:
        status = (d.status or "").upper()
        if status in ["DRAFT", "WAIT_PUTAWAY", ""]:
            d.status = "WAIT_PUTAWAY"
            d.last_update = now

    pallet_header = db.query(PalletHeader).filter(PalletHeader.pallet_id == pallet_id).first()
    if pallet_header:
        if pallet_header.po_no != po_no:
            raise ValueError(f"PA {pallet_id} đang thuộc PO {pallet_header.po_no}, không thể hoàn tất cho PO {po_no}")
        pallet_header.status = "WAIT_PUTAWAY"
        pallet_header.last_update = now

    total_sku = len(queues)
    total_qty = sum(int(q.qty_gr or 0) for q in queues)
    total_remain = sum(int(q.qty_remain_putaway or 0) for q in queues)

    db.add(AuditLog(
        operation="GR_COMPLETE_PA",
        reference_no=po_no,
        pallet_id=pallet_id,
        location_id="",
        sku="MIXED" if total_sku > 1 else queues[0].sku,
        barcode="",
        qty_before=0,
        qty_after=total_qty,
        qty_change=total_qty,
        qty_regular=total_qty,
        qty_promo=0,
        qty_total=total_qty,
        user_name=user_name,
        remark=f"Hoàn tất PA: {pallet_id}, tổng SKU={total_sku}, tổng SL={total_qty}, dòng chuyển trạng thái={changed}",
    ))

    db.commit()

    return {
        "po_no": po_no,
        "pallet_id": pallet_id,
        "total_sku": total_sku,
        "total_qty": total_qty,
        "total_remain": total_remain,
        "flow_status": "WAIT_PUTAWAY",
        "changed_lines": changed,
    }

def get_gr_history_by_po(db: Session, po_no: str, limit: int = 50):
    po_no = po_no.strip()

    if not po_no:
        return []

    return (
        db.query(InboundQueue)
        .filter(InboundQueue.po_no == po_no)
        .order_by(InboundQueue.pallet_id.asc(), InboundQueue.queue_id.desc())
        .limit(limit)
        .all()
    )



def update_gr_qty_after_confirm(
    db: Session,
    pallet_id: str,
    pcb: int,
    carton_qty: int,
    loose_qty: int,
    qty_promo: int,
    user_name: str = "developer",
    queue_id: int | None = None,
    sku: str | None = None,
    barcode: str | None = None,
):
    """Sửa số lượng GR theo từng dòng SKU trong PA.

    Với mô hình 1 PA = N SKU, không được định danh dòng sửa chỉ bằng pallet_id nữa.
    Ưu tiên queue_id; fallback pallet_id + sku/barcode để tương thích.
    """
    pallet_id = (pallet_id or "").strip().upper()
    sku = (sku or "").strip()
    barcode = (barcode or "").strip()
    pcb = int(pcb or 0)
    carton_qty = int(carton_qty or 0)
    loose_qty = int(loose_qty or 0)
    qty_promo = int(qty_promo or 0)

    if not pallet_id and not queue_id:
        raise ValueError("Thiếu mã PA hoặc dòng GR cần sửa")

    if pcb <= 0:
        raise ValueError("PCB phải lớn hơn 0")

    if carton_qty < 0 or loose_qty < 0 or qty_promo < 0:
        raise ValueError("Số lượng không được âm")

    qty_base = pcb * carton_qty + loose_qty
    qty_total = qty_base + qty_promo

    if qty_total <= 0:
        raise ValueError("Tổng số lượng mới phải lớn hơn 0")

    q = db.query(InboundQueue)
    if queue_id:
        q = q.filter(InboundQueue.queue_id == int(queue_id))
    else:
        q = q.filter(InboundQueue.pallet_id == pallet_id)
        if sku:
            q = q.filter(InboundQueue.sku == sku)
        if barcode:
            q = q.filter(InboundQueue.barcode == barcode)

    queue = q.first()

    if not queue:
        raise ValueError("Không tìm thấy dòng GR cần sửa")

    flow_status = (queue.flow_status or "").upper()
    if flow_status != "DRAFT":
        raise ValueError("Dòng này đã hoàn tất PA hoặc đã Put Away, không được sửa GR. Vui lòng nhờ quản lý kiểm tra hoặc dùng Inventory Adjustment.")

    old_qty = int(queue.qty_gr or 0)
    now = datetime.utcnow()

    queue.qty_gr = qty_total
    queue.qty_remain_putaway = qty_total
    queue.last_update = now

    pallet_detail_q = db.query(PalletDetail).filter(
        PalletDetail.pallet_id == queue.pallet_id,
        PalletDetail.sku == queue.sku,
        PalletDetail.barcode == queue.barcode,
    )
    pallet_detail = pallet_detail_q.first()

    if pallet_detail:
        pallet_detail.qty_gr = qty_total
        pallet_detail.qty_remain_putaway = qty_total
        pallet_detail.last_update = now

    gr_log = (
        db.query(GrLog)
        .filter(
            GrLog.pallet_id == queue.pallet_id,
            GrLog.sku == queue.sku,
            GrLog.barcode == queue.barcode,
        )
        .order_by(GrLog.gr_id.desc())
        .first()
    )

    if gr_log:
        gr_log.qty_gr = qty_total

    po_line = _po_line_for_barcode(db, queue.po_no, queue.barcode)
    if po_line:
        # Tính lại từ inbound_queue, gồm dòng hiện tại đã set qty_total nhưng chưa commit.
        po_line.qty_received = _calc_po_line_received(db, queue.po_no, queue.sku, queue.barcode)
        po_line.qty_remaining = max(int(po_line.qty_order or 0) - int(po_line.qty_received or 0), 0)
        po_line.status = _receipt_status(int(po_line.qty_received or 0), int(po_line.qty_order or 0))
        po_line.last_update = now

    db.add(AuditLog(
        operation="GR_EDIT_QTY",
        reference_no=queue.po_no,
        pallet_id=queue.pallet_id,
        location_id="",
        sku=queue.sku,
        barcode=queue.barcode,
        qty_before=old_qty,
        qty_after=qty_total,
        qty_change=qty_total - old_qty,
        qty_regular=qty_base,
        qty_promo=qty_promo,
        qty_total=qty_total,
        user_name=user_name,
        remark=(
            f"Sửa SL GR mixed PA: PCB={pcb}, thùng={carton_qty}, "
            f"lẻ={loose_qty}, hàng thường={qty_base}, KM={qty_promo}, tổng={qty_total}"
        ),
    ))

    db.commit()
    db.refresh(queue)

    return {
        "queue_id": queue.queue_id,
        "pallet_id": queue.pallet_id,
        "po_no": queue.po_no,
        "sku": queue.sku,
        "barcode": queue.barcode,
        "old_qty": old_qty,
        "pcb": pcb,
        "carton_qty": carton_qty,
        "loose_qty": loose_qty,
        "qty_promo": qty_promo,
        "qty_gr": qty_base,
        "qty_total": qty_total,
        "qty_remain_putaway": queue.qty_remain_putaway,
        "flow_status": queue.flow_status,
    }

def get_wait_putaway_tasks(db: Session):
    return (
        db.query(InboundQueue)
        .filter(InboundQueue.flow_status.in_(["WAIT_PUTAWAY", "PARTIAL"]))
        .order_by(InboundQueue.last_update.asc())
        .limit(100)
        .all()
    )


def _normalize_putaway_type(value: str) -> str:
    value = (value or "").strip().upper()
    if value in ["CHAN", "CHẴN", "CASE", "EVEN", "CHẵn".upper()]:
        return "CHAN"
    if value in ["LE", "LẺ", "ODD", "EACH"]:
        return "LE"
    return value


def _putaway_type_label(code: str) -> str:
    code = _normalize_putaway_type(code)
    if code == "CHAN":
        return "CHẴN"
    if code == "LE":
        return "LẺ"
    if code == "UNKNOWN":
        return "CHƯA CÓ MASTER"
    return "CHƯA XÁC ĐỊNH"


def _putaway_type_from_master(sku_type: str) -> str:
    normalized = _normalize_putaway_type(sku_type)
    if normalized in ["CHAN", "LE"]:
        return normalized
    return "UNKNOWN"


def _location_aisle(location_id: str) -> str:
    location_id = (location_id or "").strip().upper()
    if not location_id:
        return ""
    return location_id.split("-")[0].split("_")[0].split(".")[0]


def _detect_putaway_type(qty: int, pcb: int, sku_type: str = "") -> str:
    # Backward-compatible wrapper: không tự đoán chẵn/lẻ theo SL % PCB.
    return _putaway_type_from_master(sku_type)

def _location_load_score(db: Session, location_id: str) -> int:
    """Ước lượng độ đầy theo số dòng tồn tại vị trí. MVP chưa tracking pallet theo location."""
    try:
        return (
            db.query(InventoryBalance)
            .filter(InventoryBalance.location_id == location_id)
            .count()
        )
    except Exception:
        return 0


def _best_locations_for_aisles(db: Session, aisles: list[str], limit: int = 8):
    """Trả vị trí gợi ý theo dãy.

    Sprint Performance: tránh N+1 query count tồn theo từng vị trí.
    Thay vì mỗi location gọi COUNT(inventory_balance), gom location_id rồi query 1 lần.
    """
    aisle_set = {str(x or "").strip().upper() for x in aisles if str(x or "").strip()}
    if not aisle_set:
        return []

    rows = (
        db.query(LocationMaster)
        .filter(LocationMaster.status == "ACTIVE")
        .order_by(
            LocationMaster.pick_index.asc(),
            LocationMaster.location_id.asc(),
        )
        .limit(max(limit * 80, 300))
        .all()
    )

    candidates = []
    for loc in rows:
        loc_aisle = _location_aisle(loc.location_id)
        if loc_aisle in aisle_set:
            candidates.append(loc)

    if not candidates:
        return []

    location_ids = [loc.location_id for loc in candidates]
    load_map = {}
    try:
        from sqlalchemy import func
        load_rows = (
            db.query(InventoryBalance.location_id, func.count(InventoryBalance.sku))
            .filter(InventoryBalance.location_id.in_(location_ids))
            .group_by(InventoryBalance.location_id)
            .all()
        )
        load_map = {r[0]: int(r[1] or 0) for r in load_rows}
    except Exception:
        load_map = {}

    result = []
    for loc in candidates:
        loc_aisle = _location_aisle(loc.location_id)
        load_score = int(load_map.get(loc.location_id, 0) or 0)
        max_capacity = int(loc.max_capacity or 1)
        is_full = load_score >= max_capacity if max_capacity > 0 else False
        pick_index = int(loc.pick_index or 999999)

        result.append({
            "location_id": loc.location_id,
            "aisle": loc_aisle,
            "zone": loc.zone or "",
            "location_type": loc.location_type or "",
            "status": loc.status or "ACTIVE",
            "max_capacity": max_capacity,
            "current_load": load_score,
            "available_capacity": max(max_capacity - load_score, 0),
            "is_full": is_full,
            "pick_index": pick_index,
            "putaway_index": pick_index,
            "travel_sequence": pick_index,
        })

    result.sort(key=lambda x: (x["is_full"], x["putaway_index"], x["location_id"]))
    return result[:limit]

def _build_putaway_suggestions(db: Session, sku: str, barcode: str, product_name: str, category: str, putaway_type: str):
    putaway_type = _normalize_putaway_type(putaway_type)

    override_rows = (
        db.query(SkuLocationOverride)
        .filter(
            SkuLocationOverride.sku == sku,
            SkuLocationOverride.active == True,
        )
        .order_by(SkuLocationOverride.priority.asc(), SkuLocationOverride.aisle.asc())
        .all()
    )

    if override_rows:
        aisles = [x.aisle for x in override_rows]
        return {
            "source": "SKU_OVERRIDE",
            "source_label": "Rule SKU đặc biệt",
            "rows": [
                {
                    "zone": "SKU_OVERRIDE",
                    "aisle": x.aisle,
                    "priority": x.priority,
                    "note": x.reason or "SKU được chỉ định dãy riêng",
                    "putaway_type": _putaway_type_label(x.putaway_type or putaway_type),
                    "is_override": True,
                }
                for x in override_rows
            ],
            "locations": _best_locations_for_aisles(db, aisles),
        }

    q = (
        db.query(CategoryAisleMaster)
        .filter(
            CategoryAisleMaster.category == category,
            CategoryAisleMaster.active == True,
        )
    )

    if putaway_type:
        q = q.filter(
            (CategoryAisleMaster.putaway_type == putaway_type)
            | (CategoryAisleMaster.putaway_type == "")
            | (CategoryAisleMaster.putaway_type == None)
        )

    category_rows = q.order_by(CategoryAisleMaster.priority.asc(), CategoryAisleMaster.aisle.asc()).all()
    aisles = [x.aisle for x in category_rows]

    return {
        "source": "CATEGORY_RULE" if category_rows else "NO_RULE",
        "source_label": "Rule ngành hàng" if category_rows else "Chưa có rule gợi ý",
        "rows": [
            {
                "zone": x.zone,
                "aisle": x.aisle,
                "priority": x.priority,
                "note": x.note or "Dãy gợi ý theo ngành hàng",
                "putaway_type": _putaway_type_label(x.putaway_type or putaway_type),
                "is_override": False,
            }
            for x in category_rows
        ],
        "locations": _best_locations_for_aisles(db, aisles),
    }

def get_putaway_by_pallet(db: Session, pallet_id: str):
    """Load thông tin Put Away theo PA/Pallet ID.

    Sprint Performance:
    - Bulk query ProductMaster/SkuMaster cho toàn bộ SKU trong PA.
    - Tránh N+1 query: trước đây mỗi SKU query product + sku_master riêng.
    - Barcode chưa có master vẫn cho Put Away bình thường.
    """
    pallet_id = pallet_id.strip().upper()

    queues = (
        db.query(InboundQueue)
        .filter(
            InboundQueue.pallet_id == pallet_id,
            InboundQueue.flow_status.in_(["WAIT_PUTAWAY", "PARTIAL"]),
        )
        .order_by(InboundQueue.queue_id.asc())
        .all()
    )

    if not queues:
        raise ValueError("Không tìm thấy PA cần Put Away")

    sku_list = sorted({q.sku for q in queues if q.sku})
    products = {}
    sku_masters = {}

    if sku_list:
        products = {
            p.sku: p
            for p in db.query(ProductMaster).filter(ProductMaster.sku.in_(sku_list)).all()
        }
        sku_masters = {
            s.sku: s
            for s in db.query(SkuMaster).filter(SkuMaster.sku.in_(sku_list)).all()
        }

    po_no = queues[0].po_no
    total_sku = len(queues)
    total_qty_gr = sum(int(q.qty_gr or 0) for q in queues)
    total_qty_putaway = sum(int(q.qty_putaway or 0) for q in queues)
    total_qty_remain = sum(int(q.qty_remain_putaway or 0) for q in queues)

    detail_lines = []
    dominant_queue = sorted(
        queues,
        key=lambda x: int(x.qty_remain_putaway or x.qty_gr or 0),
        reverse=True,
    )[0]

    for q in queues:
        product = products.get(q.sku)
        sku_master = sku_masters.get(q.sku)
        pcb = sku_master.pcb if sku_master and sku_master.pcb else 1
        sku_type = sku_master.sku_type if sku_master else ""
        product_name = product.product_name if product else "Hàng chưa có master"
        category = product.category if product else "CHUA_CO_MASTER"
        putaway_type = _putaway_type_from_master(sku_type)

        detail_lines.append({
            "queue_id": q.queue_id,
            "po_no": q.po_no,
            "pallet_id": q.pallet_id,
            "sku": q.sku,
            "barcode": q.barcode,
            "product_name": product_name,
            "category": category,
            "pcb": int(pcb or 1),
            "sku_type": sku_type or "",
            "putaway_type": putaway_type,
            "putaway_type_label": _putaway_type_label(putaway_type),
            "qty_gr": int(q.qty_gr or 0),
            "qty_putaway": int(q.qty_putaway or 0),
            "qty_remain_putaway": int(q.qty_remain_putaway or 0),
            "flow_status": q.flow_status,
        })

    dominant_product = products.get(dominant_queue.sku)
    dominant_sku_master = sku_masters.get(dominant_queue.sku)
    dominant_pcb = dominant_sku_master.pcb if dominant_sku_master and dominant_sku_master.pcb else 1
    dominant_sku_type = dominant_sku_master.sku_type if dominant_sku_master else ""
    dominant_product_name = dominant_product.product_name if dominant_product else "Hàng chưa có master"
    dominant_category = dominant_product.category if dominant_product else "CHUA_CO_MASTER"
    dominant_putaway_type = _putaway_type_from_master(dominant_sku_type)

    suggestions = _build_putaway_suggestions(
        db=db,
        sku=dominant_queue.sku,
        barcode=dominant_queue.barcode,
        product_name=dominant_product_name,
        category=dominant_category,
        putaway_type=dominant_putaway_type,
    )

    return {
        "queue_id": dominant_queue.queue_id,
        "po_no": po_no,
        "pallet_id": pallet_id,
        "sku": dominant_queue.sku,
        "barcode": dominant_queue.barcode,
        "product_name": dominant_product_name,
        "category": dominant_category,
        "pcb": int(dominant_pcb or 1),
        "sku_type": dominant_sku_type or "",
        "putaway_type": dominant_putaway_type,
        "putaway_type_label": _putaway_type_label(dominant_putaway_type),
        "putaway_type_color": "success" if dominant_putaway_type == "CHAN" else ("warning" if dominant_putaway_type == "LE" else "secondary"),
        "qty_gr": total_qty_gr,
        "qty_putaway": total_qty_putaway,
        "qty_remain_putaway": total_qty_remain,
        "flow_status": "WAIT_PUTAWAY" if total_qty_remain > 0 else "DONE",
        "total_sku": total_sku,
        "is_mixed_sku": total_sku > 1,
        "detail_lines": detail_lines,
        "suggestion_source": suggestions["source"],
        "suggestion_source_label": suggestions["source_label"] + (" · Theo SKU số lượng lớn nhất" if total_sku > 1 else ""),
        "suggested_aisles": suggestions["rows"],
        "suggested_locations": suggestions.get("locations", []),
    }

def confirm_putaway(
    db: Session,
    queue_id: int,
    location_id: str,
    qty_putaway: int,
    user_name: str,
):
    """Put Away theo PA. Nếu PA có nhiều SKU thì cất toàn bộ các dòng SKU của PA vào cùng location."""
    location_id = location_id.strip().upper()
    scanned_aisle = _location_aisle(location_id)

    if not location_id:
        raise ValueError("Vui lòng scan vị trí")

    try:
        first_queue = db.query(InboundQueue).filter(InboundQueue.queue_id == queue_id).first()
        if not first_queue:
            raise ValueError("Không tìm thấy task Put Away")

        queues = (
            db.query(InboundQueue)
            .filter(
                InboundQueue.pallet_id == first_queue.pallet_id,
                InboundQueue.flow_status.in_(["WAIT_PUTAWAY", "PARTIAL"]),
            )
            .order_by(InboundQueue.queue_id.asc())
            .all()
        )

        if not queues:
            raise ValueError("PA không còn dòng nào cần Put Away")

        total_remain = sum(int(q.qty_remain_putaway or 0) for q in queues)
        if total_remain <= 0:
            raise ValueError("PA không còn số lượng cần Put Away")

        if qty_putaway and int(qty_putaway or 0) != total_remain:
            # Với mixed SKU pallet, Put Away là cất nguyên PA để tránh chia nhỏ sai tồn.
            raise ValueError(f"PA mixed SKU phải cất nguyên pallet. Số lượng cần cất: {total_remain}")

        location = db.query(LocationMaster).filter(LocationMaster.location_id == location_id).first()

        is_temp_location = False
        location_status = "ACTIVE"
        location_warning = ""

        task_info = get_putaway_by_pallet(db, first_queue.pallet_id)
        suggested_aisles = [str(x.get("aisle", "")).upper() for x in task_info.get("suggested_aisles", []) if x.get("aisle")]
        if location:
            scanned_aisle = _location_aisle(location.location_id) or scanned_aisle
        if suggested_aisles and scanned_aisle and scanned_aisle not in suggested_aisles:
            location_warning = f"Vị trí ngoài dãy gợi ý. Dãy gợi ý: {', '.join(suggested_aisles)}"

        if location:
            location_status = location.status or "ACTIVE"
            if location_status == "BLOCK":
                raise ValueError("Vị trí đang bị khóa, không thể Put Away")
            if location_status == "TEMP":
                is_temp_location = True
        else:
            is_temp_location = True
            db.add(MasterDataIssue(
                issue_type="LOCATION_NOT_IN_MASTER",
                sku="MIXED" if len(queues) > 1 else queues[0].sku,
                barcode="",
                pallet_id=first_queue.pallet_id,
                location_id=location_id,
                source_module="PUTAWAY",
                source_ref_id=str(first_queue.queue_id),
                created_by=user_name,
                note="Put Away PA vào vị trí tạm/chưa có trong location_master",
            ))

        now = datetime.utcnow()
        total_putaway = 0

        for queue in queues:
            line_qty = int(queue.qty_remain_putaway or 0)
            if line_qty <= 0:
                continue

            inv = db.query(InventoryBalance).filter(
                InventoryBalance.sku == queue.sku,
                InventoryBalance.location_id == location_id,
            ).first()

            if inv:
                inv.qty_onhand += line_qty
                inv.last_update = now
            else:
                db.add(InventoryBalance(
                    sku=queue.sku,
                    barcode=queue.barcode,
                    location_id=location_id,
                    qty_onhand=line_qty,
                    last_update=now,
                ))

            db.add(PutawayLog(
                queue_id=queue.queue_id,
                pallet_id=queue.pallet_id,
                sku=queue.sku,
                barcode=queue.barcode,
                location_id=location_id,
                qty_putaway=line_qty,
                user_name=user_name,
            ))

            db.add(AuditLog(
                operation="PUTAWAY",
                reference_no=queue.po_no,
                pallet_id=queue.pallet_id,
                location_id=location_id,
                sku=queue.sku,
                barcode=queue.barcode,
                qty_before=queue.qty_remain_putaway,
                qty_after=0,
                qty_change=-line_qty,
                user_name=user_name,
                remark="Cất hàng PA mixed SKU vào vị trí",
            ))

            queue.qty_putaway = int(queue.qty_putaway or 0) + line_qty
            queue.qty_remain_putaway = 0
            queue.flow_status = "DONE"
            queue.last_update = now

            pallet_detail = db.query(PalletDetail).filter(
                PalletDetail.pallet_id == queue.pallet_id,
                PalletDetail.sku == queue.sku,
                PalletDetail.barcode == queue.barcode,
            ).first()
            if pallet_detail:
                pallet_detail.qty_putaway = int(pallet_detail.qty_putaway or 0) + line_qty
                pallet_detail.qty_remain_putaway = 0
                pallet_detail.status = "DONE"
                pallet_detail.last_update = now

            total_putaway += line_qty

        pallet_header = db.query(PalletHeader).filter(PalletHeader.pallet_id == first_queue.pallet_id).first()
        if pallet_header:
            pallet_header.status = "DONE"
            pallet_header.last_update = now

        db.commit()

        return {
            "queue_id": first_queue.queue_id,
            "pallet_id": first_queue.pallet_id,
            "sku": "MIXED" if len(queues) > 1 else queues[0].sku,
            "barcode": "",
            "location_id": location_id,
            "qty_putaway": total_putaway,
            "qty_remain_putaway": 0,
            "flow_status": "DONE",
            "total_sku": len(queues),
            "location_status": location_status,
            "is_temp_location": is_temp_location,
            "location_warning": location_warning,
            "scanned_aisle": scanned_aisle,
            "suggested_aisles": suggested_aisles,
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