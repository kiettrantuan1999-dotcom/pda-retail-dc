from io import BytesIO
from datetime import datetime
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.models.tables import (
    CategoryAisleMaster,
    SkuLocationOverride,
    LocationMaster,
    PoDetail,
    ProductMaster,
    ProductBarcodeAlias,
    SkuMaster,
    DoDetail,
)
from app.services import picking_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAX_IMPORT_BYTES = 15 * 1024 * 1024
BATCH_SIZE = 2000


@router.get("/master-data/import")
def master_data_import_page(request: Request):
    return templates.TemplateResponse("master_data_import.html", {"request": request})


def excel_response(df: pd.DataFrame, filename: str):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def new_import_key(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def safe_text(value, default=""):
    if pd.isna(value):
        return default
    return str(value).strip()




def get_first_text(row, columns, default=""):
    """Lấy text theo danh sách tên cột, dùng cho file upload có header tiếng Việt/tiếng Anh."""
    for col in columns:
        if col in row.index:
            value = safe_text(row.get(col), "")
            if value:
                return value
    return default

def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def safe_bool(value, default=True):
    if pd.isna(value):
        return default
    text = str(value).strip().upper()
    if text in ["TRUE", "1", "YES", "Y", "ACTIVE", "HOẠT ĐỘNG"]:
        return True
    if text in ["FALSE", "0", "NO", "N", "INACTIVE", "KHÔNG"]:
        return False
    return default


def normalize_putaway_type(value):
    text = safe_text(value).upper()
    if text in ["CHẴN", "CHAN", "CASE", "EVEN"]:
        return "CHAN"
    if text in ["LẺ", "LE", "ODD", "EACH"]:
        return "LE"
    return text


def validate_upload(file: UploadFile):
    if file.size and file.size > MAX_IMPORT_BYTES:
        raise ValueError("File import quá lớn. Vui lòng tách file nhỏ hơn 15MB để tránh sụp web/deploy.")
    name = (file.filename or "").lower()
    if not (name.endswith(".xlsx") or name.endswith(".xls")):
        raise ValueError("Chỉ hỗ trợ file Excel .xlsx/.xls")


def read_excel_file(file: UploadFile):
    validate_upload(file)
    try:
        return pd.read_excel(file.file, dtype=str).fillna("")
    except Exception as e:
        raise ValueError(f"Không đọc được file Excel. Vui lòng kiểm tra định dạng .xlsx/.xls. Chi tiết: {e}")


def require_cols(df: pd.DataFrame, cols: list[str]):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột: {', '.join(missing)}")


def commit_batch(db: Session, counter: int):
    if counter > 0 and counter % BATCH_SIZE == 0:
        db.commit()


def import_result(inserted=0, updated=0, skipped=0, duplicate=0, conflict=0, **extra):
    data = {
        "inserted_rows": inserted,
        "updated_rows": updated,
        "skipped_rows": skipped,
        "duplicate_rows": duplicate,
        "conflict_rows": conflict,
        "imported_rows": inserted + updated,
    }
    data.update(extra)
    return {"ok": True, "data": data}


# =========================
# TEMPLATE DOWNLOAD
# =========================

@router.get("/api/master-data/template/product-master")
def download_product_master_template():
    return excel_response(pd.DataFrame([{
        "import_key": "Để trống - hệ thống tự sinh",
        "sku": "10303906",
        "barcode": "8992775347256",
        "product_name": "Sample Product",
        "uom": "EA",
        "category": "Bánh kẹo",
    }]), "product_master_template.xlsx")


@router.get("/api/master-data/template/sku-master")
def download_sku_master_template():
    return excel_response(pd.DataFrame([{
        "import_key": "Để trống - hệ thống tự sinh",
        "sku": "10303906",
        "pcb": 12,
        "mhu": 1,
        "sku_type": "CASE",
    }, {
        "import_key": "Để trống - hệ thống tự sinh",
        "sku": "10141530",
        "pcb": 1,
        "mhu": 1,
        "sku_type": "ODD",
    }]), "sku_master_template.xlsx")


@router.get("/api/master-data/template/category-aisle")
def download_category_aisle_template():
    return excel_response(pd.DataFrame([{
        "import_key": "Để trống - hệ thống tự sinh",
        "category": "Bánh kẹo",
        "putaway_type": "LE",
        "zone": "PICK_FACE_LE",
        "aisle": "A01",
        "priority": 1,
        "active": "TRUE",
        "note": "Dãy gợi ý theo ngành hàng",
    }, {
        "import_key": "Để trống - hệ thống tự sinh",
        "category": "Hóa mỹ phẩm",
        "putaway_type": "CHAN",
        "zone": "PALLET_CHAN",
        "aisle": "P01",
        "priority": 1,
        "active": "TRUE",
        "note": "Dãy chẵn theo ngành hàng",
    }]), "category_aisle_master_template.xlsx")


@router.get("/api/master-data/template/location-master")
def download_location_master_template():
    return excel_response(pd.DataFrame([{
        "import_key": "Để trống - hệ thống tự sinh",
        "location_id": "A01-01-01",
        "zone": "PICK_FACE_LE",
        "location_type": "PICK_FACE",
        "status": "ACTIVE",
        "max_capacity": 1,
        "pick_index": 1,
    }, {
        "import_key": "Để trống - hệ thống tự sinh",
        "location_id": "P01-01-01",
        "zone": "PALLET_CHAN",
        "location_type": "PALLET",
        "status": "ACTIVE",
        "max_capacity": 1,
        "pick_index": 100,
    }]), "location_master_template.xlsx")


@router.get("/api/master-data/template/sku-location-override")
def download_sku_location_override_template():
    return excel_response(pd.DataFrame([{
        "import_key": "Để trống - hệ thống tự sinh",
        "sku": "10303906",
        "barcode": "8992775347256",
        "product_name": "Sample Product",
        "putaway_type": "LE",
        "aisle": "A02",
        "priority": 1,
        "active": "TRUE",
        "reason": "SKU đặc biệt, bỏ qua rule ngành hàng",
    }]), "sku_location_override_template.xlsx")


@router.get("/api/master-data/template/po-detail")
def download_po_detail_template():
    return excel_response(pd.DataFrame([{
        "import_key": "Để trống - hệ thống tự sinh",
        "Mã đơn hàng": "PO_TEST_001",
        "Mã hàng": "10303906",
        "Tên hàng": "Sample Product",
        "Mã Barcode hàng hóa": "8992775347256",
        "ĐVT": "EA",
        "Số lượng đặt hàng": 100,
        "Trạng thái": "WAIT_GR",
        "Ghi chú": "",
    }]), "po_detail_trung_tam_dat_hang_template.xlsx")


@router.get("/api/master-data/template/do-detail")
def download_do_detail_template():
    return excel_response(pd.DataFrame([{
        "import_key": "Để trống - hệ thống tự sinh",
        "wave": 1,
        "Khung giờ": "08:15:00",
        "Loại giao": "GHN",
        "Mã chuyến": "DN001",
        "DC Sites": "1325",
        "Số STO": "4834603446",
        "DO": "7078865709",
        "Ngày tạo DO": "",
        "Mã cửa hàng": "6200",
        "Tên cửa hàng": "WM+ QTI 163 Trần Hưng Đạo",
        "Sku": "10198698",
        "Tên hàng": "CHIN-SU xốt muối ớt xanh 200g",
        "Số lượng": 2,
        "ĐVT": "CHA",
    }]), "do_detail_template.xlsx")


# =========================
# IMPORT PRODUCT MASTER
# =========================

@router.post("/api/master-data/import/product-master")
async def import_product_master(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = read_excel_file(file)
        require_cols(df, ["sku", "barcode"])
        inserted = updated = skipped = duplicate = conflict = 0
        seen_pair = set()
        seen_barcode = set()

        for idx, row in df.iterrows():
            sku = safe_text(row.get("sku")).upper()
            barcode = safe_text(row.get("barcode"))
            if not sku or not barcode:
                skipped += 1
                continue

            pair_key = (sku, barcode)
            if pair_key in seen_pair or barcode in seen_barcode:
                duplicate += 1
                continue
            seen_pair.add(pair_key)
            seen_barcode.add(barcode)

            product_name = safe_text(row.get("product_name"))
            uom = safe_text(row.get("uom"), "EA") or "EA"
            category = safe_text(row.get("category"))

            # Rule mới: 1 SKU có thể có nhiều barcode.
            # product_master giữ 1 barcode chính; product_barcode_alias giữ toàn bộ barcode scan được.
            existing = db.query(ProductMaster).filter(ProductMaster.sku == sku).first()
            barcode_owner = db.query(ProductMaster).filter(ProductMaster.barcode == barcode, ProductMaster.sku != sku).first()
            alias_owner = db.query(ProductBarcodeAlias).filter(ProductBarcodeAlias.barcode == barcode, ProductBarcodeAlias.sku != sku).first()
            if barcode_owner or alias_owner:
                conflict += 1
                continue

            is_primary = False
            if existing:
                # Không ghi đè barcode chính nếu SKU đã có; barcode mới sẽ vào alias.
                if product_name:
                    existing.product_name = product_name
                existing.uom = uom or existing.uom
                existing.category = category or existing.category
                if hasattr(existing, "import_key") and not existing.import_key:
                    existing.import_key = new_import_key("PROD")
                updated += 1
            else:
                obj = ProductMaster(sku=sku, barcode=barcode, product_name=product_name, uom=uom, category=category)
                if hasattr(obj, "import_key"):
                    obj.import_key = new_import_key("PROD")
                db.add(obj)
                inserted += 1
                is_primary = True

            alias = db.query(ProductBarcodeAlias).filter(ProductBarcodeAlias.barcode == barcode).first()
            if alias:
                alias.sku = sku
                alias.product_name = product_name
                alias.uom = uom
                alias.category = category
                alias.is_primary = is_primary or bool(existing and existing.barcode == barcode)
                alias.last_update = datetime.utcnow()
            else:
                db.add(ProductBarcodeAlias(
                    barcode=barcode,
                    sku=sku,
                    product_name=product_name,
                    uom=uom,
                    category=category,
                    is_primary=is_primary or bool(existing and existing.barcode == barcode),
                    created_at=datetime.utcnow(),
                    last_update=datetime.utcnow(),
                ))

            commit_batch(db, inserted + updated)

        db.commit()
        return import_result(inserted, updated, skipped, duplicate, conflict)
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


# =========================
# IMPORT SKU MASTER
# =========================

@router.post("/api/master-data/import/sku-master")
async def import_sku_master(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = read_excel_file(file)
        require_cols(df, ["sku"])
        inserted = updated = skipped = duplicate = 0
        seen = set()

        for _, row in df.iterrows():
            sku = safe_text(row.get("sku")).upper()
            if not sku:
                skipped += 1
                continue
            if sku in seen:
                duplicate += 1
                continue
            seen.add(sku)

            pcb = max(safe_int(row.get("pcb"), 1), 1)
            mhu = max(safe_int(row.get("mhu"), 1), 1)
            sku_type = safe_text(row.get("sku_type"), "ODD").upper() or "ODD"
            if sku_type not in ["CASE", "ODD"]:
                sku_type = "ODD"

            existing = db.query(SkuMaster).filter(SkuMaster.sku == sku).first()
            if existing:
                existing.pcb = pcb
                existing.mhu = mhu
                existing.sku_type = sku_type
                existing.last_update = datetime.utcnow()
                if hasattr(existing, "import_key") and not existing.import_key:
                    existing.import_key = new_import_key("SKU")
                updated += 1
            else:
                obj = SkuMaster(sku=sku, pcb=pcb, mhu=mhu, sku_type=sku_type, last_update=datetime.utcnow())
                if hasattr(obj, "import_key"):
                    obj.import_key = new_import_key("SKU")
                db.add(obj)
                inserted += 1
            commit_batch(db, inserted + updated)

        db.commit()
        return import_result(inserted, updated, skipped, duplicate)
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


# =========================
# IMPORT CATEGORY AISLE
# =========================

@router.post("/api/master-data/import/category-aisle")
async def import_category_aisle(mode: str = "upsert", file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = read_excel_file(file)
        require_cols(df, ["category", "zone", "aisle", "priority"])
        inserted = updated = skipped = duplicate = 0
        seen = set()

        if mode == "replace":
            db.query(CategoryAisleMaster).delete()
            db.commit()

        for _, row in df.iterrows():
            category = safe_text(row.get("category"))
            putaway_type = normalize_putaway_type(row.get("putaway_type"))
            zone = safe_text(row.get("zone"), "PICK_FACE") or "PICK_FACE"
            aisle = safe_text(row.get("aisle")).upper()
            priority = safe_int(row.get("priority"), 1)
            active = safe_bool(row.get("active"), True)
            note = safe_text(row.get("note"))

            if not category or not aisle:
                skipped += 1
                continue
            key = (category.upper(), putaway_type, aisle)
            if key in seen:
                duplicate += 1
                continue
            seen.add(key)

            existing = db.query(CategoryAisleMaster).filter(CategoryAisleMaster.category == category, CategoryAisleMaster.aisle == aisle).first()
            if existing:
                existing.zone = zone
                existing.putaway_type = putaway_type
                existing.priority = priority
                existing.active = active
                existing.note = note
                updated += 1
            else:
                db.add(CategoryAisleMaster(category=category, zone=zone, putaway_type=putaway_type, aisle=aisle, priority=priority, active=active, note=note))
                inserted += 1
            commit_batch(db, inserted + updated)

        db.commit()
        return import_result(inserted, updated, skipped, duplicate, mode=mode)
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


# =========================
# IMPORT LOCATION MASTER
# =========================

@router.post("/api/master-data/import/location-master")
async def import_location_master(mode: str = "upsert", file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = read_excel_file(file)
        require_cols(df, ["location_id"])
        inserted = updated = skipped = duplicate = 0
        seen = set()

        if mode == "replace":
            db.query(LocationMaster).delete()
            db.commit()

        for _, row in df.iterrows():
            location_id = safe_text(row.get("location_id")).upper()
            if not location_id:
                skipped += 1
                continue
            if location_id in seen:
                duplicate += 1
                continue
            seen.add(location_id)

            zone = safe_text(row.get("zone"), "")
            location_type = safe_text(row.get("location_type"), "PICK_FACE") or "PICK_FACE"
            status = safe_text(row.get("status"), "ACTIVE").upper() or "ACTIVE"
            max_capacity = max(safe_int(row.get("max_capacity"), 1), 1)
            pick_index = safe_int(row.get("pick_index"), 999999)

            existing = db.query(LocationMaster).filter(LocationMaster.location_id == location_id).first()
            if existing:
                existing.zone = zone
                existing.location_type = location_type
                existing.status = status
                existing.max_capacity = max_capacity
                existing.pick_index = pick_index
                if hasattr(existing, "import_key") and not existing.import_key:
                    existing.import_key = new_import_key("LOC")
                updated += 1
            else:
                obj = LocationMaster(location_id=location_id, zone=zone, location_type=location_type, status=status, max_capacity=max_capacity, pick_index=pick_index)
                if hasattr(obj, "import_key"):
                    obj.import_key = new_import_key("LOC")
                db.add(obj)
                inserted += 1
            commit_batch(db, inserted + updated)

        db.commit()
        return import_result(inserted, updated, skipped, duplicate, mode=mode)
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


# =========================
# IMPORT SKU LOCATION OVERRIDE
# =========================

@router.post("/api/master-data/import/sku-location-override")
async def import_sku_location_override(mode: str = "upsert", file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = read_excel_file(file)
        require_cols(df, ["sku", "aisle"])
        inserted = updated = skipped = duplicate = 0
        seen = set()

        if mode == "replace":
            db.query(SkuLocationOverride).delete()
            db.commit()

        for _, row in df.iterrows():
            sku = safe_text(row.get("sku")).upper()
            aisle = safe_text(row.get("aisle")).upper()
            if not sku or not aisle:
                skipped += 1
                continue
            key = (sku, aisle)
            if key in seen:
                duplicate += 1
                continue
            seen.add(key)

            barcode = safe_text(row.get("barcode"))
            product_name = safe_text(row.get("product_name"))
            putaway_type = normalize_putaway_type(row.get("putaway_type"))
            priority = safe_int(row.get("priority"), 1)
            active = safe_bool(row.get("active"), True)
            reason = safe_text(row.get("reason"))

            existing = db.query(SkuLocationOverride).filter(SkuLocationOverride.sku == sku, SkuLocationOverride.aisle == aisle).first()
            if existing:
                existing.barcode = barcode
                existing.product_name = product_name
                existing.putaway_type = putaway_type
                existing.priority = priority
                existing.active = active
                existing.reason = reason
                existing.last_update = datetime.utcnow()
                updated += 1
            else:
                db.add(SkuLocationOverride(sku=sku, barcode=barcode, product_name=product_name, putaway_type=putaway_type, aisle=aisle, priority=priority, active=active, reason=reason, last_update=datetime.utcnow()))
                inserted += 1
            commit_batch(db, inserted + updated)

        db.commit()
        return import_result(inserted, updated, skipped, duplicate, mode=mode)
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


# =========================
# IMPORT PO DETAIL
# =========================

@router.post("/api/master-data/import/po-detail")
async def import_po_detail(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = read_excel_file(file)
        col_map = {
            "Mã đơn hàng": "po_no",
            "Mã hàng": "sku",
            "Tên hàng": "product_name",
            "Mã Barcode hàng hóa": "barcode",
            "Số lượng đặt hàng": "qty_order",
        }
        require_cols(df, list(col_map.keys()))

        # Aggregate duplicate PO + SKU lines before touching DB.
        # Đây là điểm giảm lag chính: không query/update DB từng dòng raw Excel.
        grouped = {}
        skipped = 0
        for _, row in df.iterrows():
            po_no = safe_text(row.get("Mã đơn hàng"))
            sku = safe_text(row.get("Mã hàng")).upper()
            barcode = safe_text(row.get("Mã Barcode hàng hóa"))
            qty_order = safe_int(row.get("Số lượng đặt hàng"), 0)
            if not po_no or not sku or not barcode or qty_order <= 0:
                skipped += 1
                continue
            key = (po_no, sku)
            if key not in grouped:
                grouped[key] = {
                    "po_no": po_no,
                    "sku": sku,
                    "barcode": barcode,
                    "product_name": safe_text(row.get("Tên hàng")),
                    "qty_order": 0,
                }
            grouped[key]["qty_order"] += qty_order

        keys = list(grouped.keys())
        po_set = {po for po, _ in keys}
        existing_map = {}
        if po_set:
            existing_rows = db.query(PoDetail).filter(PoDetail.po_no.in_(list(po_set))).all()
            existing_map = {(r.po_no, r.sku): r for r in existing_rows}

        inserted = updated = 0
        duplicate = max(len(df) - skipped - len(grouped), 0)
        now = datetime.utcnow()

        for key, row in grouped.items():
            existing = existing_map.get(key)
            if existing:
                existing.barcode = row["barcode"]
                existing.product_name = row["product_name"]
                existing.qty_order = row["qty_order"]
                existing.qty_remaining = max(row["qty_order"] - int(existing.qty_received or 0), 0)
                if int(existing.qty_received or 0) > row["qty_order"]:
                    existing.status = "DƯ"
                elif int(existing.qty_received or 0) == row["qty_order"]:
                    existing.status = "ĐỦ"
                else:
                    existing.status = "WAIT_GR"
                existing.last_update = now
                updated += 1
            else:
                db.add(PoDetail(
                    po_no=row["po_no"],
                    sku=row["sku"],
                    barcode=row["barcode"],
                    product_name=row["product_name"],
                    qty_order=row["qty_order"],
                    qty_received=0,
                    qty_remaining=row["qty_order"],
                    status="WAIT_GR",
                    created_at=now,
                    last_update=now,
                ))
                inserted += 1

            commit_batch(db, inserted + updated)

        db.commit()
        return import_result(inserted, updated, skipped, duplicate)
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


@router.post("/api/master-data/import/do-detail")
async def import_do_detail(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = read_excel_file(file)
        required_cols = ["wave", "Khung giờ", "Loại giao", "DC Sites", "Số STO", "DO", "Mã cửa hàng", "Tên cửa hàng", "Sku", "Tên hàng", "Số lượng", "ĐVT"]
        require_cols(df, required_cols)

        # Aggregate duplicate DO + store + SKU lines. This prevents duplicate natural-key collisions and keeps picking qty correct.
        grouped = {}
        skipped = 0
        do_set = set()
        store_set = set()
        for _, row in df.iterrows():
            do_no = safe_text(row.get("DO"))
            sku = safe_text(row.get("Sku")).upper()
            store_id = safe_text(row.get("Mã cửa hàng"))
            qty_do = safe_int(row.get("Số lượng"), 0)
            if not do_no or not sku or not store_id or qty_do <= 0:
                skipped += 1
                continue
            key = (do_no, store_id, sku)
            if key not in grouped:
                grouped[key] = {
                    "wave": safe_text(row.get("wave")),
                    "khung_gio": safe_text(row.get("Khung giờ")),
                    "loai_giao": safe_text(row.get("Loại giao")),
                    "trip_no": get_first_text(row, ["Mã chuyến", "Ma chuyen", "Trip", "trip", "trip_no", "trip no"], ""),
                    "dc_site": safe_text(row.get("DC Sites")),
                    "sto_no": safe_text(row.get("Số STO")),
                    "do_created_date": safe_text(row.get("Ngày tạo DO")),
                    "do_no": do_no,
                    "store_id": store_id,
                    "store_name": safe_text(row.get("Tên cửa hàng")),
                    "sku": sku,
                    "product_name": safe_text(row.get("Tên hàng")),
                    "uom": get_first_text(row, ["ĐVT", "DVT", "Đơn vị tính", "Don vi tinh", "uom", "UOM"], ""),
                    "qty_do": 0,
                }
            grouped[key]["qty_do"] += qty_do
            do_set.add(do_no)
            store_set.add(store_id)

        # PO detail không dùng logic xóa stale của DO. Giữ các PO khác để không làm mất lịch sử nhập hàng.

        inserted = updated = 0
        duplicate = max(len(df) - skipped - len(grouped), 0)
        for row in grouped.values():
            product = db.query(ProductMaster).filter(ProductMaster.sku == row["sku"]).first()
            data = {
                "wave": row["wave"],
                "khung_gio": row["khung_gio"],
                "loai_giao": row["loai_giao"],
                "trip_no": row.get("trip_no", ""),
                "dc_site": row["dc_site"],
                "sto_no": row["sto_no"],
                "do_created_date": row["do_created_date"],
                "store_name": row["store_name"],
                "barcode": product.barcode if product else "",
                "product_name": row["product_name"],
                "uom": row["uom"],
                "qty_do": row["qty_do"],
                "qty_remain": row["qty_do"],
                "status": "WAIT_PICK",
            }
            existing = db.query(DoDetail).filter(DoDetail.do_no == row["do_no"], DoDetail.store_id == row["store_id"], DoDetail.sku == row["sku"]).first()
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.add(DoDetail(do_no=row["do_no"], store_id=row["store_id"], sku=row["sku"], **data))
                inserted += 1
            commit_batch(db, inserted + updated)

        db.commit()

        created_picking = 0
        for store_id in store_set:
            result = picking_service.tao_phieu_lay_hang_theo_cua_hang(db, store_id)
            created_picking += result["so_phieu_lay_hang"]

        # Sprint 40 guard: ép chuẩn lại mã phiếu ngay sau khi tạo.
        # Tránh trường hợp service cũ/cache vẫn sinh dạng MA_CUA_HANG-C/L.
        picking_service.chuan_hoa_ma_phieu_theo_ngay_do(db, store_ids=list(store_set))
        db.commit()

        return import_result(inserted, updated, skipped, duplicate, so_do=len(do_set), so_cua_hang=len(store_set), so_phieu_lay_hang=created_picking, stale_deleted=stale_deleted)
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
