from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import warehouse_service as svc

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/putaway", tags=["Cất hàng"])


@router.get("", response_class=HTMLResponse)
def putaway_list(
    request: Request,
    db: Session = Depends(get_db),
):
    tasks = svc.get_wait_putaway_tasks(db)

    return templates.TemplateResponse(
        "putaway/list.html",
        {
            "request": request,
            "tasks": tasks,
        },
    )


@router.get("/tasks")
def redirect_wrong_tasks_url():
    return RedirectResponse(url="/putaway")


@router.get("/scan")
def redirect_scan_url(pallet_id: str | None = None):
    if pallet_id:
        return RedirectResponse(url=f"/putaway/{pallet_id.strip().upper()}")
    return RedirectResponse(url="/putaway/scan-pa")


@router.get("/scan-pa", response_class=HTMLResponse)
def putaway_scan_pa_page(request: Request):
    return templates.TemplateResponse(
        "putaway/scan_pa.html",
        {
            "request": request,
        },
    )


@router.get("/{pallet_id}", response_class=HTMLResponse)
def putaway_scan(
    request: Request,
    pallet_id: str,
    db: Session = Depends(get_db),
):
    pallet_id = (pallet_id or "").strip().upper()

    task = None
    error = None

    try:
        if not pallet_id:
            raise ValueError("Vui lòng scan PA/Pallet")
        task = svc.get_putaway_by_pallet(db, pallet_id)
    except Exception as exc:
        error = str(exc) or "Không tìm thấy nhiệm vụ cất hàng"

    return templates.TemplateResponse(
        "putaway/scan.html",
        {
            "request": request,
            "task": task,
            "error": error,
        },
    )
