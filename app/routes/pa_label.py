from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.pa_label_service import generate_pa_labels

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def current_user(request: Request):
    return request.session.get("user")


def require_login(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=302)
    return None


@router.get("/pa-label", response_class=HTMLResponse)
def pa_label_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "pa_label.html",
        {
            "request": request,
            "user": current_user(request),
            "labels": [],
            "qty": 20,
            "error": None,
        },
    )


@router.post("/pa-label", response_class=HTMLResponse)
def pa_label_generate(
    request: Request,
    qty: int = Form(...),
):
    redirect = require_login(request)
    if redirect:
        return redirect

    labels = []
    error = None

    try:
        labels = generate_pa_labels(qty)
    except Exception as exc:
        error = str(exc)

    return templates.TemplateResponse(
        "pa_label.html",
        {
            "request": request,
            "user": current_user(request),
            "labels": labels,
            "qty": qty,
            "error": error,
        },
    )
