import traceback

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard_service import lay_du_lieu_bang_dieu_khien

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/supervisor/dashboard", response_class=HTMLResponse)
async def supervisor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        user = request.session.get("user")

        if not user:
            return RedirectResponse(url="/login", status_code=302)

        # Sprint 46: tắt dashboard realtime mặc định để tăng tốc app.
        # Chỉ load dữ liệu nặng khi user chủ động bấm "Tải dashboard".
        load = (request.query_params.get("load") or "").strip()
        if load != "1":
            return templates.TemplateResponse(
                "supervisor/dashboard_disabled.html",
                {
                    "request": request,
                    "user": user,
                    "role_label": user.get("role", ""),
                },
            )

        bang_dieu_khien = lay_du_lieu_bang_dieu_khien(db)

        return templates.TemplateResponse(
            "supervisor/dashboard.html",
            {
                "request": request,
                "user": user,
                "role_label": user.get("role", ""),
                "bang_dieu_khien": bang_dieu_khien,
                "dashboard": bang_dieu_khien,
            },
        )

    except Exception:
        error_text = traceback.format_exc()
        return HTMLResponse(
            content=f"<pre>{error_text}</pre>",
            status_code=500,
        )