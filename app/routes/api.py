from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import warehouse_service as svc
from app.services.log_service import write_operation_log

router = APIRouter(prefix="/api")


def username(request: Request):
    u = request.session.get("user")
    if not u:
        raise ValueError("Chưa đăng nhập")
    return u["user_name"]


def ok(data=None):
    return {"ok": True, "data": data or {}}


def fail(e: Exception):
    return {"ok": False, "error": str(e)}


@router.post("/gr/confirm")
def gr_confirm(
    request: Request,
    po_no: str = Form(...),
    pallet_id: str = Form(...),
    barcode: str = Form(...),
    qty_gr: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        result = svc.confirm_gr(db, po_no.strip(), pallet_id.strip(), barcode.strip(), qty_gr, username(request))
        return ok(result)
    except Exception as e:
        db.rollback()
        return fail(e)


@router.get("/inventory/search")
def inventory_search(q: str = "", db: Session = Depends(get_db)):
    rows = svc.search_inventory(db, q.strip())
    return ok({"rows": [
        {"sku": r.sku, "barcode": r.barcode, "location_id": r.location_id, "qty_onhand": r.qty_onhand}
        for r in rows
    ]})
