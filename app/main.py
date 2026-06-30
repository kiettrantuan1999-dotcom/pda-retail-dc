from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.routes import picking
from app.routes import pack
from app.routes import supervisor
from app.routes import audit
from app.routes import admin
from app.routes import staging
from app.core.config import SECRET_KEY
from app.routes import pages, auth, api, putaway, master_data, inventory, pa_label
from app.middleware.error_middleware import ErrorLoggingMiddleware
from app.middleware.performance_middleware import PerformanceMiddleware

app = FastAPI(
    title="Supra WES",
    version="1.0.0"
)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(PerformanceMiddleware, slow_ms=300)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(master_data.router)
app.include_router(inventory.router)
app.include_router(putaway.router)
app.include_router(picking.router)
app.include_router(pack.router)
app.include_router(supervisor.router)
app.include_router(audit.router)
app.include_router(admin.router)
app.include_router(staging.router)
app.include_router(pa_label.router)
