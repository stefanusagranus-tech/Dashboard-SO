"""
Rate Limiting Middleware — slowapi
===================================
Batasi jumlah request per IP.

Limit default:
- Semua endpoint: 60 req/menit
- Endpoint /chat: 20 req/menit
- Endpoint /parse: 30 req/menit
- Endpoint /rekap: 30 req/menit
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


# =========================================================
# HELPER — Ambil IP asli dari Cloudflare / proxy
# =========================================================
def get_real_ip(request) -> str:
    """
    Ambil IP asli user dari header proxy.
    Cloudflare kirim CF-Connecting-IP.
    """
    _ip = (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP")
        or get_remote_address(request)
        or "unknown"
    )
    return _ip


# =========================================================
# LIMITER INSTANCE
# =========================================================
limiter = Limiter(
    key_func=get_real_ip,              # ← pakai IP asli
    default_limits=["60/minute"],      # default limit semua endpoint
)


# =========================================================
# HELPER — Register ke FastAPI app
# =========================================================
def setup_rate_limit(app):
    """
    Register slowapi ke FastAPI app.
    Panggil di main.py setelah app = FastAPI().
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    return app


# =========================================================
# EXPORT
# =========================================================
__all__ = [
    "limiter",
    "setup_rate_limit",
    "RateLimitExceeded",
]