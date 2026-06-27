from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tables import OperationLog, ErrorLog, AppUser, AppRole
from app.core.permissions import has_permission, ROLE_LABELS

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def current_user(request: Request):
    return request.session.get("user")


def require_login(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=302)
    return None


@router.get("/", response_class=HTMLResponse)
def root(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    role = user.get("role", "worker")

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": user,
            "role_label": ROLE_LABELS.get(role, role),
            "can_dashboard": has_permission(role, "DASHBOARD_VIEW"),
            "can_logs": has_permission(role, "OPERATION_LOG_VIEW"),
            "can_users": has_permission(role, "USER_MANAGE"),
        },
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
        },
    )


@router.get("/gr", response_class=HTMLResponse)
def gr_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "gr.html",
        {
            "request": request,
            "user": current_user(request),
        },
    )


@router.get("/pack", response_class=HTMLResponse)
def pack_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "pack.html",
        {
            "request": request,
            "user": current_user(request),
        },
    )


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "inventory.html",
        {
            "request": request,
            "user": current_user(request),
        },
    )


@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "audit.html",
        {
            "request": request,
            "user": current_user(request),
        },
    )


@router.get("/management", response_class=HTMLResponse)
def management_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    role = user.get("role", "worker")

    if not has_permission(role, "DASHBOARD_VIEW"):
        return RedirectResponse("/", status_code=302)

    kpi = {
        "users": db.query(AppUser).count(),
        "operations": db.query(OperationLog).count(),
        "errors": db.query(ErrorLog).count(),
        "roles": db.query(AppRole).count(),
    }

    return templates.TemplateResponse(
        "management.html",
        {
            "request": request,
            "user": user,
            "kpi": kpi,
        },
    )


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    role = user.get("role", "worker")

    if not has_permission(role, "OPERATION_LOG_VIEW"):
        return RedirectResponse("/", status_code=302)

    operations = (
        db.query(OperationLog)
        .order_by(OperationLog.log_id.desc())
        .limit(100)
        .all()
    )

    errors = (
        db.query(ErrorLog)
        .order_by(ErrorLog.error_id.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "user": user,
            "operations": operations,
            "errors": errors,
        },
    )


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = current_user(request)
    role = user.get("role", "worker")

    if not has_permission(role, "USER_MANAGE"):
        return RedirectResponse("/", status_code=302)

    users = (
        db.query(AppUser)
        .order_by(AppUser.user_id.asc())
        .all()
    )

    roles = (
        db.query(AppRole)
        .order_by(AppRole.role_id.asc())
        .all()
    )

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "roles": roles,
        },
    )