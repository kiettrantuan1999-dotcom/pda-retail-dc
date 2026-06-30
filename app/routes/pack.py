from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.pack_service import get_pack_logs, list_wait_pack_tasks
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/pack", tags=["Pack"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def pack_page(request: Request, db: Session = Depends(get_db)):
    tasks = list_wait_pack_tasks(db)

    return templates.TemplateResponse(
        "pack/index.html",
        {"request": request, "tasks": tasks},
    )


@router.get("/logs", response_class=HTMLResponse)
def pack_logs_page(request: Request, db: Session = Depends(get_db)):
    logs = get_pack_logs(db)

    return templates.TemplateResponse(
        "pack/logs.html",
        {
            "request": request,
            "logs": logs,
        },
    )