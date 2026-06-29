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
def redirect_scan_url():
    return RedirectResponse(url="/putaway/scan-pa")
@router.get("/scan-pa", response_class=HTMLResponse)
def putaway_scan_pa_page(request: Request):
    return templates.TemplateResponse(
        "putaway/scan_pa.html",
        {
            "request": request,
        },
    )


@router.get("/{queue_id}", response_class=HTMLResponse)
def putaway_scan(
    request: Request,
    queue_id: int,
    db: Session = Depends(get_db),
):
    tasks = svc.get_wait_putaway_tasks(db)

    task = None
    for t in tasks:
        if int(t.queue_id) == int(queue_id):
            try:
                task = svc.get_putaway_by_pallet(db, t.pallet_id)
            except Exception:
                task = None
            break

    return templates.TemplateResponse(
        "putaway/scan.html",
        {
            "request": request,
            "task": task,
            "error": None if task else "Không tìm thấy nhiệm vụ cất hàng",
        },
    )