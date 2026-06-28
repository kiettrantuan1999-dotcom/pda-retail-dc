from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.permissions import (
    PERMISSION_LABELS,
    PERMISSION_MODULES,
    ROLE_LABELS,
    ROLE_PERMISSIONS,
    has_permission,
)
from app.db.session import get_db
from app.models.tables import AppRole
from app.services.admin_service import (
    DEFAULT_RESET_PASSWORD,
    create_user,
    get_user_by_id,
    list_settings,
    list_users,
    reset_password,
    update_settings,
    update_user,
)
from app.services.log_service import write_operation_log

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")


ROLE_OPTIONS = ["worker", "supervisor", "admin"]


def current_user(request: Request):
    return request.session.get("user")


def require_admin(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    role = user.get("role", "worker")
    if not has_permission(role, "USER_MANAGE"):
        return RedirectResponse("/", status_code=302)

    return None


def _bool_from_form(value: str | None) -> bool:
    return value == "ACTIVE"


def _roles(db: Session):
    rows = db.query(AppRole).filter(AppRole.is_active == True).order_by(AppRole.role_id.asc()).all()
    if rows:
        return [r.role_code for r in rows]
    return ROLE_OPTIONS


def _permission_rows():
    all_permissions = sorted(PERMISSION_LABELS.keys(), key=lambda code: (PERMISSION_MODULES.get(code, ""), code))
    rows = []
    for code in all_permissions:
        rows.append({
            "code": code,
            "name": PERMISSION_LABELS.get(code, code),
            "module": PERMISSION_MODULES.get(code, "Khác"),
            "roles": {
                role_code: code in ROLE_PERMISSIONS.get(role_code, set())
                for role_code in ROLE_LABELS.keys()
            },
        })
    return rows


@router.get("/roles", response_class=HTMLResponse)
def roles_page(request: Request):
    redirect = require_admin(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "admin/roles.html",
        {
            "request": request,
            "user": current_user(request),
            "role_labels": ROLE_LABELS,
            "roles": list(ROLE_LABELS.keys()),
            "permission_rows": _permission_rows(),
        },
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    message: str = Query(""),
    error: str = Query(""),
    db: Session = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect

    settings = list_settings(db)
    db.commit()

    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": current_user(request),
            "settings": settings,
            "message": message,
            "error": error,
        },
    )


@router.post("/settings")
async def save_settings(request: Request, db: Session = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect

    admin_user = current_user(request) or {}
    admin_name = admin_user.get("user_name", "")
    form = await request.form()

    try:
        update_settings(db, dict(form), updated_by=admin_name)
        write_operation_log(
            db,
            event_type="CẬP_NHẬT_CẤU_HÌNH",
            module_name="QUẢN_TRỊ",
            user_name=admin_name,
            reference_type="SYSTEM_SETTING",
            reference_id="ADMIN_SETTINGS",
            status="SUCCESS",
            message="Cập nhật cấu hình hệ thống",
        )
        db.commit()
        return RedirectResponse("/admin/settings?message=Đã lưu cấu hình hệ thống", status_code=302)
    except Exception as exc:
        db.rollback()
        return RedirectResponse(f"/admin/settings?error=Lưu cấu hình thất bại: {exc}", status_code=302)


@router.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    q: str = Query(""),
    role: str = Query(""),
    status: str = Query(""),
    message: str = Query(""),
    error: str = Query(""),
    db: Session = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect

    users = list_users(db, q=q, role=role, status=status)

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": current_user(request),
            "users": users,
            "roles": _roles(db),
            "role_labels": ROLE_LABELS,
            "filters": {"q": q, "role": role, "status": status},
            "message": message,
            "error": error,
        },
    )


@router.get("/users/new", response_class=HTMLResponse)
def new_user_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "admin/user_form.html",
        {
            "request": request,
            "user": current_user(request),
            "mode": "create",
            "target_user": None,
            "roles": _roles(db),
            "role_labels": ROLE_LABELS,
            "error": "",
        },
    )


@router.post("/users/new")
def create_user_post(
    request: Request,
    user_name: str = Form(...),
    password: str = Form(""),
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    role: str = Form("worker"),
    status: str = Form("ACTIVE"),
    db: Session = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect

    admin_user = current_user(request) or {}
    admin_name = admin_user.get("user_name", "")

    try:
        created = create_user(
            db,
            user_name=user_name,
            password=password or DEFAULT_RESET_PASSWORD,
            full_name=full_name,
            email=email,
            phone=phone,
            role=role,
            is_active=_bool_from_form(status),
            created_by=admin_name,
        )
        write_operation_log(
            db,
            event_type="TẠO_USER",
            module_name="QUẢN_TRỊ",
            user_name=admin_name,
            reference_type="APP_USER",
            reference_id=created.user_name,
            status="SUCCESS",
            message=f"Tạo người dùng {created.user_name}",
        )
        db.commit()
        return RedirectResponse("/admin/users?message=Đã tạo người dùng", status_code=302)
    except ValueError as exc:
        db.rollback()
        return templates.TemplateResponse(
            "admin/user_form.html",
            {
                "request": request,
                "user": current_user(request),
                "mode": "create",
                "target_user": None,
                "roles": _roles(db),
                "role_labels": ROLE_LABELS,
                "error": str(exc),
            },
            status_code=400,
        )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def edit_user_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        return RedirectResponse("/admin/users?error=Không tìm thấy người dùng", status_code=302)

    return templates.TemplateResponse(
        "admin/user_form.html",
        {
            "request": request,
            "user": current_user(request),
            "mode": "edit",
            "target_user": target_user,
            "roles": _roles(db),
            "role_labels": ROLE_LABELS,
            "error": "",
        },
    )


@router.post("/users/{user_id}/edit")
def edit_user_post(
    user_id: int,
    request: Request,
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    role: str = Form("worker"),
    status: str = Form("ACTIVE"),
    db: Session = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        return RedirectResponse("/admin/users?error=Không tìm thấy người dùng", status_code=302)

    admin_user = current_user(request) or {}
    admin_name = admin_user.get("user_name", "")

    update_user(
        db,
        target_user,
        full_name=full_name,
        email=email,
        phone=phone,
        role=role,
        is_active=_bool_from_form(status),
    )
    write_operation_log(
        db,
        event_type="SỬA_USER",
        module_name="QUẢN_TRỊ",
        user_name=admin_name,
        reference_type="APP_USER",
        reference_id=target_user.user_name,
        status="SUCCESS",
        message=f"Cập nhật người dùng {target_user.user_name}",
    )
    db.commit()

    return RedirectResponse("/admin/users?message=Đã cập nhật người dùng", status_code=302)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        return RedirectResponse("/admin/users?error=Không tìm thấy người dùng", status_code=302)

    admin_user = current_user(request) or {}
    admin_name = admin_user.get("user_name", "")

    reset_password(db, target_user)
    write_operation_log(
        db,
        event_type="RESET_MẬT_KHẨU",
        module_name="QUẢN_TRỊ",
        user_name=admin_name,
        reference_type="APP_USER",
        reference_id=target_user.user_name,
        status="SUCCESS",
        message=f"Reset mật khẩu người dùng {target_user.user_name}",
    )
    db.commit()

    return RedirectResponse(
        f"/admin/users?message=Đã reset mật khẩu về {DEFAULT_RESET_PASSWORD}",
        status_code=302,
    )


@router.post("/users/{user_id}/toggle")
def toggle_user_status(user_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        return RedirectResponse("/admin/users?error=Không tìm thấy người dùng", status_code=302)

    admin_user = current_user(request) or {}
    admin_name = admin_user.get("user_name", "")

    if target_user.user_name == admin_name and target_user.is_active:
        return RedirectResponse("/admin/users?error=Không thể khóa chính user đang đăng nhập", status_code=302)

    target_user.is_active = not target_user.is_active
    db.add(target_user)

    write_operation_log(
        db,
        event_type="ĐỔI_TRẠNG_THÁI_USER",
        module_name="QUẢN_TRỊ",
        user_name=admin_name,
        reference_type="APP_USER",
        reference_id=target_user.user_name,
        status="SUCCESS",
        message=f"Đổi trạng thái {target_user.user_name}",
    )
    db.commit()

    return RedirectResponse("/admin/users?message=Đã đổi trạng thái người dùng", status_code=302)
