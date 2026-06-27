from io import BytesIO
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.tables import DoDetail
from app.services import picking_service

from app.db.session import get_db
from app.models.tables import (
    CategoryAisleMaster,
    PoDetail,
    ProductMaster,
    SkuMaster,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/master-data/import")
def master_data_import_page(request: Request):
    return templates.TemplateResponse(
        "master_data_import.html",
        {"request": request},
    )


def excel_response(df: pd.DataFrame, filename: str):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")

    output.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


def safe_text(value, default=""):
    if pd.isna(value):
        return default
    return str(value).strip()


def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


# =========================
# TEMPLATE DOWNLOAD
# =========================

@router.get("/api/master-data/template/product-master")
def download_product_master_template():
    df = pd.DataFrame(
        [
            {
                "sku": "10303906",
                "barcode": "8992775347256",
                "product_name": "Sample Product",
                "uom": "EA",
                "category": "Bánh kẹo",
            }
        ]
    )

    return excel_response(df, "product_master_template.xlsx")


@router.get("/api/master-data/template/sku-master")
def download_sku_master_template():
    df = pd.DataFrame(
        [
            {
                "sku": "10303906",
                "pcb": 12,
                "mhu": 1,
                "sku_type": "CASE",
            },
            {
                "sku": "10141530",
                "pcb": 1,
                "mhu": 1,
                "sku_type": "ODD",
            },
        ]
    )

    return excel_response(df, "sku_master_template.xlsx")


@router.get("/api/master-data/template/category-aisle")
def download_category_aisle_template():
    df = pd.DataFrame(
        [
            {
                "category": "Bánh kẹo",
                "zone": "PICK_FACE",
                "aisle": "A01",
                "priority": 1,
                "note": "Dãy gợi ý theo ngành hàng",
            }
        ]
    )

    return excel_response(df, "category_aisle_master_template.xlsx")


@router.get("/api/master-data/template/po-detail")
def download_po_detail_template():
    df = pd.DataFrame(
        [
            {
                "Mã đơn hàng": "PO_TEST_001",
                "Mã hàng": "10303906",
                "Tên hàng": "Sample Product",
                "Mã Barcode hàng hóa": "8992775347256",
                "ĐVT": "EA",
                "Số lượng đặt hàng": 100,
                "Trạng thái": "WAIT_GR",
                "Ghi chú": "",
            }
        ]
    )

    return excel_response(df, "po_detail_trung_tam_dat_hang_template.xlsx")

@router.get("/api/master-data/template/do-detail")
def download_do_detail_template():
    df = pd.DataFrame(
        [
            {
                "wave": 1,
                "Khung giờ": "08:15:00",
                "Loại giao": "GHN",
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
            }
        ]
    )

    return excel_response(df, "do_detail_template.xlsx")


# =========================
# IMPORT PRODUCT MASTER
# =========================

@router.post("/api/master-data/import/product-master")
async def import_product_master(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    df = pd.read_excel(file.file)

    required_cols = ["sku", "barcode"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        return {
            "ok": False,
            "error": f"Thiếu cột: {', '.join(missing)}",
        }

    inserted = 0
    updated = 0
    skipped = 0

    try:
        for _, row in df.iterrows():
            sku = safe_text(row.get("sku")).upper()
            barcode = safe_text(row.get("barcode"))
            product_name = safe_text(row.get("product_name"))
            uom = safe_text(row.get("uom"), "EA") or "EA"
            category = safe_text(row.get("category"))

            if not sku or not barcode:
                skipped += 1
                continue

            existing = (
                db.query(ProductMaster)
                .filter(ProductMaster.sku == sku)
                .first()
            )

            if existing:
                existing.barcode = barcode
                existing.product_name = product_name
                existing.uom = uom
                existing.category = category
                updated += 1
            else:
                db.add(
                    ProductMaster(
                        sku=sku,
                        barcode=barcode,
                        product_name=product_name,
                        uom=uom,
                        category=category,
                    )
                )
                inserted += 1

        db.commit()

        return {
            "ok": True,
            "data": {
                "inserted_rows": inserted,
                "updated_rows": updated,
                "skipped_rows": skipped,
                "imported_rows": inserted + updated,
            },
        }

    except Exception as e:
        db.rollback()
        return {
            "ok": False,
            "error": str(e),
        }


# =========================
# IMPORT SKU MASTER
# =========================

@router.post("/api/master-data/import/sku-master")
async def import_sku_master(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    df = pd.read_excel(file.file)

    required_cols = ["sku"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        return {
            "ok": False,
            "error": f"Thiếu cột: {', '.join(missing)}",
        }

    inserted = 0
    updated = 0
    skipped = 0

    try:
        for _, row in df.iterrows():
            sku = safe_text(row.get("sku")).upper()
            pcb = safe_int(row.get("pcb"), 1)
            mhu = safe_int(row.get("mhu"), 1)
            sku_type = safe_text(row.get("sku_type"), "ODD").upper() or "ODD"

            if not sku:
                skipped += 1
                continue

            if pcb <= 0:
                pcb = 1

            if mhu <= 0:
                mhu = 1

            if sku_type not in ["CASE", "ODD"]:
                sku_type = "ODD"

            existing = (
                db.query(SkuMaster)
                .filter(SkuMaster.sku == sku)
                .first()
            )

            if existing:
                existing.pcb = pcb
                existing.mhu = mhu
                existing.sku_type = sku_type
                existing.last_update = datetime.utcnow()
                updated += 1
            else:
                db.add(
                    SkuMaster(
                        sku=sku,
                        pcb=pcb,
                        mhu=mhu,
                        sku_type=sku_type,
                        last_update=datetime.utcnow(),
                    )
                )
                inserted += 1

        db.commit()

        return {
            "ok": True,
            "data": {
                "inserted_rows": inserted,
                "updated_rows": updated,
                "skipped_rows": skipped,
                "imported_rows": inserted + updated,
            },
        }

    except Exception as e:
        db.rollback()
        return {
            "ok": False,
            "error": str(e),
        }


# =========================
# IMPORT CATEGORY AISLE
# =========================

@router.post("/api/master-data/import/category-aisle")
async def import_category_aisle(
    mode: str = "upsert",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    df = pd.read_excel(file.file)

    required_cols = ["category", "zone", "aisle", "priority"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        return {
            "ok": False,
            "error": f"Thiếu cột: {', '.join(missing)}",
        }

    count = 0

    try:
        if mode == "replace":
            db.query(CategoryAisleMaster).delete()
            db.flush()

        for _, row in df.iterrows():
            category = safe_text(row.get("category"))
            zone = safe_text(row.get("zone"), "PICK_FACE") or "PICK_FACE"
            aisle = safe_text(row.get("aisle")).upper()
            priority = safe_int(row.get("priority"), 1)
            note = safe_text(row.get("note"))

            if not category or not aisle:
                continue

            existing = (
                db.query(CategoryAisleMaster)
                .filter(
                    CategoryAisleMaster.category == category,
                    CategoryAisleMaster.aisle == aisle,
                )
                .first()
            )

            if existing:
                existing.zone = zone
                existing.priority = priority
                existing.note = note
            else:
                db.add(
                    CategoryAisleMaster(
                        category=category,
                        zone=zone,
                        aisle=aisle,
                        priority=priority,
                        note=note,
                    )
                )

            count += 1

        db.commit()

        return {
            "ok": True,
            "data": {
                "imported_rows": count,
                "mode": mode,
            },
        }

    except Exception as e:
        db.rollback()
        return {
            "ok": False,
            "error": str(e),
        }


# =========================
# IMPORT PO DETAIL
# =========================

@router.post("/api/master-data/import/po-detail")
async def import_po_detail(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    df = pd.read_excel(file.file)

    col_map = {
        "Mã đơn hàng": "po_no",
        "Mã hàng": "sku",
        "Tên hàng": "product_name",
        "Mã Barcode hàng hóa": "barcode",
        "Số lượng đặt hàng": "qty_order",
    }

    missing = [c for c in col_map.keys() if c not in df.columns]

    if missing:
        return {
            "ok": False,
            "error": f"Thiếu cột: {', '.join(missing)}",
        }

    count = 0

    try:
        for _, row in df.iterrows():
            po_no = safe_text(row.get("Mã đơn hàng"))
            sku = safe_text(row.get("Mã hàng")).upper()
            barcode = safe_text(row.get("Mã Barcode hàng hóa"))
            product_name = safe_text(row.get("Tên hàng"))
            qty_order = safe_int(row.get("Số lượng đặt hàng"), 0)

            if not po_no or not sku or not barcode or qty_order <= 0:
                continue

            existing = (
                db.query(PoDetail)
                .filter(
                    PoDetail.po_no == po_no,
                    PoDetail.sku == sku,
                )
                .first()
            )

            if existing:
                existing.barcode = barcode
                existing.product_name = product_name
                existing.qty_order = qty_order
                existing.qty_remaining = max(qty_order - existing.qty_received, 0)

                if existing.qty_remaining == 0:
                    existing.status = "DONE"
                else:
                    existing.status = "WAIT_GR"

            else:
                db.add(
                    PoDetail(
                        po_no=po_no,
                        sku=sku,
                        barcode=barcode,
                        product_name=product_name,
                        qty_order=qty_order,
                        qty_received=0,
                        qty_remaining=qty_order,
                        status="WAIT_GR",
                    )
                )

            count += 1

        db.commit()

        return {
            "ok": True,
            "data": {
                "imported_rows": count,
            },
        }

    except Exception as e:
        db.rollback()
        return {
            "ok": False,
            "error": str(e),
        }
    
@router.post("/api/master-data/import/do-detail")
async def import_do_detail(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    df = pd.read_excel(file.file)

    required_cols = [
        "wave",
        "Khung giờ",
        "Loại giao",
        "DC Sites",
        "Số STO",
        "DO",
        "Mã cửa hàng",
        "Tên cửa hàng",
        "Sku",
        "Tên hàng",
        "Số lượng",
        "ĐVT",
    ]

    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        return {
            "ok": False,
            "error": f"Thiếu cột: {', '.join(missing)}",
        }

    imported = 0
    skipped = 0
    do_set = set()

    try:
        for _, row in df.iterrows():
            do_no = safe_text(row.get("DO"))
            sku = safe_text(row.get("Sku")).upper()
            store_id = safe_text(row.get("Mã cửa hàng"))
            qty_do = safe_int(row.get("Số lượng"), 0)

            if not do_no or not sku or not store_id or qty_do <= 0:
                skipped += 1
                continue

            product = (
                db.query(ProductMaster)
                .filter(ProductMaster.sku == sku)
                .first()
            )

            existing = (
                db.query(DoDetail)
                .filter(
                    DoDetail.do_no == do_no,
                    DoDetail.store_id == store_id,
                    DoDetail.sku == sku,
                )
                .first()
            )

            data = {
                "wave": safe_text(row.get("wave")),
                "khung_gio": safe_text(row.get("Khung giờ")),
                "loai_giao": safe_text(row.get("Loại giao")),
                "dc_site": safe_text(row.get("DC Sites")),
                "sto_no": safe_text(row.get("Số STO")),
                "do_created_date": safe_text(row.get("Ngày tạo DO")),
                "store_name": safe_text(row.get("Tên cửa hàng")),
                "barcode": product.barcode if product else "",
                "product_name": safe_text(row.get("Tên hàng")),
                "uom": safe_text(row.get("ĐVT")),
                "qty_do": qty_do,
                "qty_remain": qty_do,
                "status": "WAIT_PICK",
            }

            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                db.add(
                    DoDetail(
                        do_no=do_no,
                        store_id=store_id,
                        sku=sku,
                        **data,
                    )
                )

            imported += 1
            do_set.add(do_no)

        db.flush()

        created_picking = 0

        for do_no in do_set:
            result = picking_service.tao_phieu_lay_hang_theo_do(db, do_no)
            created_picking += result["so_phieu_lay_hang"]

        return {
            "ok": True,
            "data": {
                "imported_rows": imported,
                "skipped_rows": skipped,
                "so_do": len(do_set),
                "so_phieu_lay_hang": created_picking,
            },
        }

    except Exception as e:
        db.rollback()
        return {
            "ok": False,
            "error": str(e),
        }