from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import picking_service as svc

router = APIRouter(prefix="/picking", tags=["Phiếu lấy hàng"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def danh_sach_phieu(request: Request, db: Session = Depends(get_db)):
    rows = svc.danh_sach_phieu_lay_hang(db)

    return templates.TemplateResponse(
        "picking/list.html",
        {
            "request": request,
            "rows": rows,
        },
    )


@router.get("/{picking_id}", response_class=HTMLResponse)
def chi_tiet_phieu(
    request: Request,
    picking_id: int,
    db: Session = Depends(get_db),
):
    header, details, total_label_qty = svc.chi_tiet_phieu_lay_hang(db, picking_id)

    return templates.TemplateResponse(
        "picking/detail.html",
        {
            "request": request,
            "header": header,
            "details": details,
            "total_label_qty": total_label_qty,
        },
    )


@router.get("/{picking_id}/print", response_class=HTMLResponse)
def in_phieu_lay_hang(
    request: Request,
    picking_id: int,
    db: Session = Depends(get_db),
):
    header, details, total_label_qty = svc.chi_tiet_phieu_lay_hang(db, picking_id)

    return templates.TemplateResponse(
        "picking/print.html",
        {
            "request": request,
            "header": header,
            "details": details,
            "total_label_qty": total_label_qty,
        },
    )