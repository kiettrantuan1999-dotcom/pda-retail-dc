from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
router=APIRouter(); templates=Jinja2Templates(directory='app/templates')
def current_user(request:Request): return request.session.get('user')
def guard(request):
    if not current_user(request): return RedirectResponse('/login',status_code=302)
@router.get('/',response_class=HTMLResponse)
def root(request:Request):
    g=guard(request)
    if g: return g
    return templates.TemplateResponse('home.html',{'request':request,'user':current_user(request)})
@router.get('/login',response_class=HTMLResponse)
def login_page(request:Request): return templates.TemplateResponse('login.html',{'request':request,'error':None})
for_path={'/gr':'gr.html','/putaway':'putaway.html','/pack':'pack.html','/inventory':'inventory.html','/audit':'audit.html'}
def make_page(tpl):
    def page(request:Request):
        g=guard(request)
        if g: return g
        return templates.TemplateResponse(tpl,{'request':request,'user':current_user(request)})
    return page
for path,tpl in for_path.items(): router.add_api_route(path,make_page(tpl),methods=['GET'],response_class=HTMLResponse)
