from fastapi import APIRouter, Request, Depends, Form, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import warehouse_service as svc
from app.services.log_service import write_operation_log
from app.services import pack_service
from app.services.pack_service import get_pack_by_do, confirm_pack
from app.core.version import APP_VERSION

router = APIRouter(prefix="/api")


def username(request: Request):
    u = request.session.get("user")

    if not u:
        return "developer"

    return u["user_name"]


def ok(data=None):
    return {"ok": True, "data": data or {}}


def fail(e: Exception):
    return {"ok": False, "error": str(e)}


@router.get("/app/version")
def app_version():
    return {"ok": True, "version": APP_VERSION}


@router.get("/gr/product/{barcode}")
def gr_product_info(
    barcode: str,
    po_no: str = Query(""),
    db: Session = Depends(get_db),
):
    try:
        return ok(svc.get_product_scan_info(db, barcode.strip(), po_no=po_no.strip()))
    except Exception as e:
        return fail(e)


@router.get("/gr/po/{po_no}")
def gr_po_detail(
    po_no: str,
    db: Session = Depends(get_db),
):
    try:
        return ok(svc.get_gr_po_detail_summary(db, po_no.strip()))
    except Exception as e:
        return fail(e)


@router.post("/gr/confirm")
def gr_confirm(
    request: Request,
    po_no: str = Form(...),
    pallet_id: str = Form(...),
    barcode: str = Form(...),
    carton_qty: int = Form(0),
    loose_qty: int = Form(0),
    pcb: int = Form(1),
    qty_promo: int = Form(0),
    db: Session = Depends(get_db),
):
    try:
        result = svc.confirm_gr(
            db=db,
            po_no=po_no.strip(),
            pallet_id=pallet_id.strip(),
            barcode=barcode.strip(),
            carton_qty=carton_qty,
            loose_qty=loose_qty,
            pcb=pcb,
            qty_promo=qty_promo,
            user_name=username(request),
        )
        return ok(result)
    except Exception as e:
        db.rollback()
        return fail(e)

@router.get("/gr/history/{po_no}")
def gr_history(
    po_no: str,
    db: Session = Depends(get_db),
):
    try:
        # Performance: service đã enrich master data bằng bulk query.
        # Tránh gọi get_product_scan_info cho từng dòng history vì gây N+1 query và làm PDA chậm.
        return ok({"rows": svc.get_gr_history_payload_fast(db, po_no.strip())})
    except Exception as e:
        return fail(e)




@router.post("/gr/update-qty")
def gr_update_qty(
    request: Request,
    pallet_id: str = Form(...),
    queue_id: int | None = Form(None),
    sku: str = Form(""),
    barcode: str = Form(""),
    pcb: int = Form(...),
    carton_qty: int = Form(0),
    loose_qty: int = Form(0),
    qty_promo: int = Form(0),
    db: Session = Depends(get_db),
):
    try:
        result = svc.update_gr_qty_after_confirm(
            db=db,
            pallet_id=pallet_id.strip(),
            pcb=pcb,
            carton_qty=carton_qty,
            loose_qty=loose_qty,
            qty_promo=qty_promo,
            user_name=username(request),
            queue_id=queue_id,
            sku=sku,
            barcode=barcode,
        )
        return ok(result)
    except Exception as e:
        db.rollback()
        return fail(e)


@router.post("/gr/complete-pa")
def gr_complete_pa(
    request: Request,
    po_no: str = Form(...),
    pallet_id: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        result = svc.complete_gr_pallet(
            db=db,
            po_no=po_no.strip(),
            pallet_id=pallet_id.strip(),
            user_name=username(request),
        )
        return ok(result)
    except Exception as e:
        db.rollback()
        return fail(e)


@router.post("/gr/confirm-po")
def gr_confirm_po(
    request: Request,
    po_no: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        result = svc.confirm_gr_po(
            db=db,
            po_no=po_no.strip(),
            user_name=username(request),
        )
        return ok(result)
    except Exception as e:
        db.rollback()
        return fail(e)


@router.get("/putaway/tasks")
def putaway_tasks(db: Session = Depends(get_db)):
    try:
        rows = svc.get_wait_putaway_tasks(db)

        return ok({
            "rows": [
                {
                    "queue_id": r.queue_id,
                    "po_no": r.po_no,
                    "pallet_id": r.pallet_id,
                    "sku": r.sku,
                    "barcode": r.barcode,
                    "qty_gr": r.qty_gr,
                    "qty_putaway": r.qty_putaway,
                    "qty_remain_putaway": r.qty_remain_putaway,
                    "flow_status": r.flow_status,
                }
                for r in rows
            ]
        })
    except Exception as e:
        return fail(e)

@router.get("/putaway/pallet/{pallet_id}")
def get_putaway_by_pallet(
    pallet_id: str,
    db: Session = Depends(get_db),
):
    try:
        result = svc.get_putaway_by_pallet(
            db,
            pallet_id.strip()
        )
        return ok(result)

    except Exception as e:
        return fail(e)
    
@router.post("/putaway/confirm")
def putaway_confirm(
    request: Request,
    queue_id: int = Form(...),
    location_id: str = Form(...),
    qty_putaway: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        result = svc.confirm_putaway(
            db=db,
            queue_id=queue_id,
            location_id=location_id.strip(),
            qty_putaway=qty_putaway,
            user_name=username(request),
        )
        return ok(result)
    except Exception as e:
        db.rollback()
        return fail(e)


@router.get("/inventory/search-basic")
def inventory_search(q: str = "", db: Session = Depends(get_db)):
    rows = svc.search_inventory(db, q.strip())
    return ok({"rows": [
        {"sku": r.sku, "barcode": r.barcode, "location_id": r.location_id, "qty_onhand": r.qty_onhand}
        for r in rows
    ]})
@router.get("/pack/do/{do_no}")
def get_pack_do(
    do_no: str,
    db: Session = Depends(get_db),
):
    try:
        result = pack_service.get_pack_by_do(db, do_no)

        if result.get("ok") is False:
            return result

        return ok(result)
    except Exception as e:
        return fail(e)


@router.post("/pack/confirm")
def pack_confirm(
    request: Request,
    do_no: str = Form(...),
    actual_package_qty: int = Form(...),
    picker_name: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
            result = pack_service.confirm_pack(
                db=db,
                do_no=do_no,
                actual_package_qty=actual_package_qty,
                picker_name=picker_name,
                user_name=username(request),
                device_name=request.headers.get("User-Agent", ""),
            )

            if result.get("ok") is False:
                return result

            return ok(result)
    except Exception as e:
        db.rollback()
        return fail(e)


