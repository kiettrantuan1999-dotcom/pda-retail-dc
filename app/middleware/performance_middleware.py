import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Log thời gian xử lý từng request để tìm endpoint chậm.

    Không ghi body/request payload để tránh lộ dữ liệu vận hành.
    Chỉ log các request mất >= slow_ms.
    """

    def __init__(self, app, slow_ms: int = 300):
        super().__init__(app)
        self.slow_ms = int(slow_ms or 300)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)

        if elapsed_ms >= self.slow_ms:
            path = request.url.path
            method = request.method
            status = response.status_code
            print(f"PERF_SLOW {method} {path} {status} {elapsed_ms}ms")

        return response
