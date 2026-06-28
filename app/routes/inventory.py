from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import inventory_service as svc
from app.core.permissions import has_permission

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def current_user(request: Request):
    return request.session.get("user")


def require_login(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=302)
    return None


def username(request: Request):
    user = current_user(request)
    return user.get("user_name", "developer") if user else "developer"


def require_supervisor(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    user = current_user(request)
    role = user.get("role", "worker")
    if not has_permission(role, "DASHBOARD_VIEW"):
        return RedirectResponse("/inventory", status_code=302)
    return None


def ok(data=None):
    return {"ok": True, "data": data or {}}


def fail(e: Exception):
    return {"ok": False, "error": str(e)}


@router.get("/inventory", response_class=HTMLResponse)
def inventory_home(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    role = user.get("role", "worker")
    return templates.TemplateResponse(
        "inventory/index.html",
        {
            "request": request,
            "user": user,
            "can_supervisor": has_permission(role, "DASHBOARD_VIEW"),
        },
    )


@router.get("/inventory/inquiry", response_class=HTMLResponse)
def inventory_inquiry_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("inventory/inquiry.html", {"request": request, "user": current_user(request)})


@router.get("/inventory/counts", response_class=HTMLResponse)
def inventory_counts_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "inventory/counts.html",
        {"request": request, "user": current_user(request), "counts": svc.list_counts(db)},
    )


@router.get("/inventory/counts/new", response_class=HTMLResponse)
def inventory_new_count_page(request: Request):
    redirect = require_supervisor(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("inventory/new_count.html", {"request": request, "user": current_user(request), "error": None})


@router.post("/inventory/counts/new", response_class=HTMLResponse)
def inventory_create_count_page(
    request: Request,
    count_name: str = Form(""),
    locations_text: str = Form(...),
    db: Session = Depends(get_db),
):
    redirect = require_supervisor(request)
    if redirect:
        return redirect

    try:
        header = svc.create_count(db, count_name, locations_text, username(request))
        return RedirectResponse(f"/inventory/counts/{header.count_no}", status_code=302)
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            "inventory/new_count.html",
            {"request": request, "user": current_user(request), "error": str(e)},
        )


@router.get("/inventory/counts/{count_no}", response_class=HTMLResponse)
def inventory_count_detail_page(count_no: str, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    role = user.get("role", "worker")
    header = svc.get_count_header(db, count_no)
    details = svc.get_count_details(db, count_no)

    return templates.TemplateResponse(
        "inventory/count_detail.html",
        {
            "request": request,
            "user": user,
            "header": header,
            "details": details,
            "can_approve": has_permission(role, "DASHBOARD_VIEW"),
        },
    )


@router.get("/inventory/counts/{count_no}/scan", response_class=HTMLResponse)
def inventory_count_scan_page(count_no: str, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect
    header = svc.get_count_header(db, count_no)
    return templates.TemplateResponse("inventory/count_scan.html", {"request": request, "user": current_user(request), "header": header})


@router.get("/api/inventory/search")
def api_inventory_search(q: str = "", db: Session = Depends(get_db)):
    try:
        return ok({"rows": svc.search_inventory(db, q)})
    except Exception as e:
        return fail(e)


@router.get("/api/inventory/counts/{count_no}/scan")
def api_count_scan(count_no: str, location_id: str = "", barcode: str = "", db: Session = Depends(get_db)):
    try:
        d = svc.get_count_task_by_scan(db, count_no, location_id, barcode)
        return ok({
            "detail_id": d.detail_id,
            "count_no": d.count_no,
            "location_id": d.location_id,
            "sku": d.sku,
            "barcode": d.barcode,
            "product_name": d.product_name,
            "expected_qty": d.expected_qty,
            "count_qty": d.count_qty,
            "variance_qty": d.variance_qty,
            "status": d.status,
        })
    except Exception as e:
        return fail(e)


@router.post("/api/inventory/counts/save")
def api_save_count(
    request: Request,
    detail_id: int = Form(...),
    count_qty: int = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        d = svc.save_count_result(db, detail_id, count_qty, username(request), note)
        return ok({
            "detail_id": d.detail_id,
            "location_id": d.location_id,
            "sku": d.sku,
            "barcode": d.barcode,
            "expected_qty": d.expected_qty,
            "count_qty": d.count_qty,
            "variance_qty": d.variance_qty,
            "status": d.status,
        })
    except Exception as e:
        db.rollback()
        return fail(e)


@router.post("/api/inventory/counts/{count_no}/approve")
def api_approve_count(count_no: str, request: Request, db: Session = Depends(get_db)):
    redirect = require_supervisor(request)
    if redirect:
        return fail(ValueError("Bạn không có quyền duyệt kiểm kê"))
    try:
        h = svc.approve_count(db, count_no, username(request))
        return ok({"count_no": h.count_no, "status": h.status})
    except Exception as e:
        db.rollback()
        return fail(e)
