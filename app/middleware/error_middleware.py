import traceback

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from app.db.session import SessionLocal
from app.services.log_service import write_error_log


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            # In lỗi thật ra terminal để debug local.
            print("\n========== SUPRA WES ERROR ==========")
            print(f"PATH: {request.method} {request.url.path}")
            print(traceback.format_exc())
            print("=====================================\n")

            db = SessionLocal()
            try:
                user = request.session.get("user") if hasattr(request, "session") else None
                user_name = user.get("user_name", "") if isinstance(user, dict) else ""

                write_error_log(
                    db,
                    module_name="HỆ THỐNG",
                    function_name=f"{request.method} {request.url.path}",
                    user_name=user_name,
                    error=exc,
                    request_payload={
                        "method": request.method,
                        "url": str(request.url),
                        "query_params": dict(request.query_params),
                    },
                    ip_address=request.client.host if request.client else "",
                    device_info=request.headers.get("user-agent", ""),
                )
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "error": "Hệ thống đang lỗi. Vui lòng báo quản lý hoặc thử lại.",
                },
            )
