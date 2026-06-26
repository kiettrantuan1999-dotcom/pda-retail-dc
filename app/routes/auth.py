from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.services.auth_service import authenticate_user
from app.services.log_service import write_operation_log

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/login")
def login(
    request: Request,
    user_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, user_name, password)
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")

    if not user:
        write_operation_log(
            db,
            event_type="ĐĂNG_NHẬP",
            module_name="XÁC_THỰC",
            user_name=user_name,
            status="FAIL",
            message="Sai tên đăng nhập hoặc mật khẩu",
            ip_address=ip,
            device_info=ua,
        )
        db.commit()
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Sai tên đăng nhập hoặc mật khẩu"},
            status_code=401,
        )

    request.session["user"] = {
        "user_name": user.user_name,
        "role": user.role,
    }

    write_operation_log(
        db,
        event_type="ĐĂNG_NHẬP",
        module_name="XÁC_THỰC",
        user_name=user.user_name,
        status="SUCCESS",
        message="Đăng nhập thành công",
        ip_address=ip,
        device_info=ua,
    )
    db.commit()

    return RedirectResponse("/", status_code=302)


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user") or {}
    user_name = user.get("user_name", "")

    write_operation_log(
        db,
        event_type="ĐĂNG_XUẤT",
        module_name="XÁC_THỰC",
        user_name=user_name,
        status="SUCCESS",
        message="Đăng xuất",
        ip_address=request.client.host if request.client else "",
        device_info=request.headers.get("user-agent", ""),
    )
    db.commit()

    request.session.clear()
    return RedirectResponse("/login", status_code=302)
