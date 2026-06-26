from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from app.db.session import get_db
from app.services.auth_service import authenticate_user
router=APIRouter(); templates=Jinja2Templates(directory='app/templates')
@router.post('/login')
def login(request:Request,user_name:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    user=authenticate_user(db,user_name,password)
    if not user: return templates.TemplateResponse('login.html',{'request':request,'error':'Sai user hoặc password'},status_code=401)
    request.session['user']={'user_name':user.user_name,'role':user.role}
    return RedirectResponse('/',status_code=302)
@router.get('/logout')
def logout(request:Request): request.session.clear(); return RedirectResponse('/login',status_code=302)
