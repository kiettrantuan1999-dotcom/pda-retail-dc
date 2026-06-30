from datetime import datetime

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import picking_service as svc

router = APIRouter(prefix="/picking", tags=["Phiếu lấy hàng"])
templates = Jinja2Templates(directory="app/templates")


def username(request: Request):
    u = request.session.get("user")
    if not u:
        return "developer"
    return u.get("user_name", "developer")


@router.get("", response_class=HTMLResponse)
def danh_sach_phieu(request: Request, db: Session = Depends(get_db)):
    rows = svc.danh_sach_phieu_lay_hang(db)

    return templates.TemplateResponse(
        "picking/list.html",
        {
            "request": request,
            "rows": rows,
            "title": "Tất cả phiếu lấy hàng",
        },
    )


@router.get("/cho-in", response_class=HTMLResponse)
def phieu_cho_in(request: Request, db: Session = Depends(get_db)):
    rows = svc.danh_sach_phieu_lay_hang(db, print_status="WAIT_PRINT")

    return templates.TemplateResponse(
        "picking/list.html",
        {
            "request": request,
            "rows": rows,
            "title": "Phiếu chờ in",
        },
    )


@router.get("/da-in", response_class=HTMLResponse)
def phieu_da_in(request: Request, db: Session = Depends(get_db)):
    rows = svc.danh_sach_phieu_lay_hang(db, print_status="PRINTED")

    return templates.TemplateResponse(
        "picking/list.html",
        {
            "request": request,
            "rows": rows,
            "title": "Phiếu đã in",
        },
    )



@router.get("/print-bulk", response_class=HTMLResponse)
def in_hang_loat_phieu_lay_hang(
    request: Request,
    print_status: str = Query("WAIT_PRINT"),
    limit: int = Query(80),
    db: Session = Depends(get_db),
):
    # In hàng loạt theo trạng thái. Mặc định chỉ in phiếu chờ in.
    limit = max(1, min(int(limit or 80), 200))
    picking_ids = svc.lay_danh_sach_id_in_hang_loat(db, print_status=print_status, limit=limit)
    pages = svc.du_lieu_in_hang_loat(db, picking_ids, username(request))

    return templates.TemplateResponse(
        "picking/print_bulk.html",
        {
            "request": request,
            "pages": pages,
            "print_time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "print_status": print_status,
            "limit": limit,
        },
    )

@router.get("/{picking_id}", response_class=HTMLResponse)
def chi_tiet_phieu(
    request: Request,
    picking_id: int,
    db: Session = Depends(get_db),
):
    header, details, total_label_qty = svc.chi_tiet_phieu_lay_hang(db, picking_id)
    pick_lines = svc.tong_hop_dong_pick(details)
    stats = svc.thong_ke_phieu(details)

    return templates.TemplateResponse(
        "picking/detail.html",
        {
            "request": request,
            "header": header,
            "details": details,
            "pick_lines": pick_lines,
            "stats": stats,
            "total_label_qty": total_label_qty,
        },
    )


@router.get("/{picking_id}/print", response_class=HTMLResponse)
def in_phieu_lay_hang(
    request: Request,
    picking_id: int,
    db: Session = Depends(get_db),
):
    # Sprint 31: dùng safe reader cho trang in để tránh lỗi 500 khi DB local
    # chưa đồng bộ đủ cột mới như barcode/uom/pcb/label_qty.
    header, details, total_label_qty = svc.chi_tiet_phieu_lay_hang_print_safe(db, picking_id)
    pick_lines = svc.tong_hop_dong_pick(details)
    stats = svc.thong_ke_phieu(details)

    response = templates.TemplateResponse(
        "picking/print.html",
        {
            "request": request,
            "header": header,
            "details": details,
            "pick_lines": pick_lines,
            "stats": stats,
            "total_label_qty": total_label_qty,
            "print_time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        },
    )

    # Đánh dấu đã in sau khi tạo response thành công. Nếu update lỗi thì không làm vỡ trang in.
    try:
        svc.danh_dau_da_in_safe(db, picking_id, username(request))
    except Exception as exc:
        print("WARN picking print update failed:", repr(exc))

    return response
