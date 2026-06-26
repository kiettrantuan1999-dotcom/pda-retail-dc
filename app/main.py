from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import SECRET_KEY
from app.routes import pages, auth, api
app=FastAPI(title='PDA Retail DC Execution App',version='2.0.0')
app.add_middleware(SessionMiddleware,secret_key=SECRET_KEY)
app.mount('/static',StaticFiles(directory='app/static'),name='static')
app.include_router(pages.router); app.include_router(auth.router); app.include_router(api.router)
