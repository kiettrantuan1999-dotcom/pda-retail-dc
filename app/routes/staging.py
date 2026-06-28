from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.permissions import has_permission
from app.db.session import get_db
from app.services.staging_service import (
    confirm_staging,
    get_staging_summary,
    list_wait_staging,
)

router = APIRouter(prefix="/staging", tags=["Tập kết hàng"])
templates = Jinja2Templates(directory="app/templates")


def current_user(request: Request):
    return request.session.get("user")


def require_staging_permission(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    role = user.get("role", "worker")
    if not has_permission(role, "STAGING_USE"):
        return RedirectResponse("/", status_code=302)

    return None


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def staging_page(
    request: Request,
    do_no: str = Query(""),
    db: Session = Depends(get_db),
):
    redirect = require_staging_permission(request)
    if redirect:
        return redirect

    summary = None
    error = ""

    if do_no.strip():
        result = get_staging_summary(db, do_no)
        if result.get("ok"):
            summary = result
        else:
            error = result.get("message", "Không tìm thấy dữ liệu tập kết.")

    wait_rows = list_wait_staging(db)

    return templates.TemplateResponse(
        "staging/index.html",
        {
            "request": request,
            "user": current_user(request),
            "do_no": do_no,
            "summary": summary,
            "error": error,
            "wait_rows": wait_rows,
        },
    )


@router.post("/confirm", response_class=HTMLResponse)
def staging_confirm(
    request: Request,
    do_no: str = Form(...),
    physical_check: str = Form(""),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    redirect = require_staging_permission(request)
    if redirect:
        return redirect

    if physical_check != "YES":
        wait_rows = list_wait_staging(db)
        result = get_staging_summary(db, do_no)
        return templates.TemplateResponse(
            "staging/index.html",
            {
                "request": request,
                "user": current_user(request),
                "do_no": do_no,
                "summary": result if result.get("ok") else None,
                "error": "Vui lòng tick xác nhận đã kiểm đủ hàng thực tế trước khi bấm hoàn tất.",
                "success": "",
                "wait_rows": wait_rows,
            },
        )

    user = current_user(request) or {}
    user_name = user.get("user_name", "developer")

    try:
        result = confirm_staging(
            db=db,
            scan_code=do_no,
            user_name=user_name,
            remark=remark,
        )
        if not result.get("ok"):
            raise ValueError(result.get("message", "Xác nhận tập kết thất bại."))

        wait_rows = list_wait_staging(db)
        return templates.TemplateResponse(
            "staging/index.html",
            {
                "request": request,
                "user": current_user(request),
                "do_no": result.get("do_no", do_no),
                "summary": result,
                "error": "",
                "success": result.get("message", "Đã xác nhận tập kết."),
                "wait_rows": wait_rows,
            },
        )
    except Exception as e:
        db.rollback()
        wait_rows = list_wait_staging(db)
        result = get_staging_summary(db, do_no)
        return templates.TemplateResponse(
            "staging/index.html",
            {
                "request": request,
                "user": current_user(request),
                "do_no": do_no,
                "summary": result if result.get("ok") else None,
                "error": str(e),
                "success": "",
                "wait_rows": wait_rows,
            },
        )
