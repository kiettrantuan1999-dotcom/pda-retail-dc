from datetime import datetime, time

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.permissions import has_permission
from app.db.session import get_db
from app.models.tables import AuditLog

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def current_user(request: Request):
    return request.session.get("user")


def require_audit_permission(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    role = user.get("role", "worker")
    if not has_permission(role, "OPERATION_LOG_VIEW") and not has_permission(role, "AUDIT_USE"):
        return RedirectResponse("/", status_code=302)

    return None


def _clean(value: str) -> str:
    return (value or "").strip()


def _parse_date_start(value: str):
    value = _clean(value)
    if not value:
        return None
    return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time.min)


def _parse_date_end(value: str):
    value = _clean(value)
    if not value:
        return None
    return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time.max)


@router.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    q: str = Query(""),
    operation: str = Query(""),
    sku: str = Query(""),
    barcode: str = Query(""),
    pallet_id: str = Query(""),
    location_id: str = Query(""),
    reference_no: str = Query(""),
    user_name: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    db: Session = Depends(get_db),
):
    redirect = require_audit_permission(request)
    if redirect:
        return redirect

    query = db.query(AuditLog)

    if _clean(q):
        like = f"%{_clean(q)}%"
        query = query.filter(
            (AuditLog.sku.ilike(like))
            | (AuditLog.barcode.ilike(like))
            | (AuditLog.pallet_id.ilike(like))
            | (AuditLog.location_id.ilike(like))
            | (AuditLog.reference_no.ilike(like))
            | (AuditLog.user_name.ilike(like))
        )

    if _clean(operation):
        query = query.filter(AuditLog.operation == _clean(operation).upper())
    if _clean(sku):
        query = query.filter(AuditLog.sku.ilike(f"%{_clean(sku)}%"))
    if _clean(barcode):
        query = query.filter(AuditLog.barcode.ilike(f"%{_clean(barcode)}%"))
    if _clean(pallet_id):
        query = query.filter(AuditLog.pallet_id.ilike(f"%{_clean(pallet_id)}%"))
    if _clean(location_id):
        query = query.filter(AuditLog.location_id.ilike(f"%{_clean(location_id)}%"))
    if _clean(reference_no):
        query = query.filter(AuditLog.reference_no.ilike(f"%{_clean(reference_no)}%"))
    if _clean(user_name):
        query = query.filter(AuditLog.user_name.ilike(f"%{_clean(user_name)}%"))

    try:
        start_dt = _parse_date_start(date_from)
        end_dt = _parse_date_end(date_to)
        if start_dt:
            query = query.filter(AuditLog.event_time >= start_dt)
        if end_dt:
            query = query.filter(AuditLog.event_time <= end_dt)
        error = ""
    except ValueError:
        error = "Định dạng ngày không hợp lệ. Dùng YYYY-MM-DD."

    rows = query.order_by(AuditLog.event_time.desc()).limit(300).all()

    return templates.TemplateResponse(
        "audit.html",
        {
            "request": request,
            "user": current_user(request),
            "rows": rows,
            "error": error,
            "filters": {
                "q": q,
                "operation": operation,
                "sku": sku,
                "barcode": barcode,
                "pallet_id": pallet_id,
                "location_id": location_id,
                "reference_no": reference_no,
                "user_name": user_name,
                "date_from": date_from,
                "date_to": date_to,
            },
            "operations": ["GR", "PUTAWAY", "COUNT", "ADJUST", "PACK", "STAGING_CONFIRM"],
        },
    )
