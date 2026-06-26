from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import SECRET_KEY
from app.routes import pages, auth, api
from app.middleware.error_middleware import ErrorLoggingMiddleware

app = FastAPI(title="Supra WES", version="1.0.0")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(ErrorLoggingMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(api.router)
