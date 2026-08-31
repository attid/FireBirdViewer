"""HTTP security helpers for the public interface boundary."""

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = logging.getLogger("firebirdviewer")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach request IDs and conservative browser security headers."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", "").strip() or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


def public_error(request: Request, exc: Exception, message: str) -> str:
    """Log the failure and return its complete diagnostic text to the administrator."""
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    log.error(
        "request_failed request_id=%s",
        request_id,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return str(exc)
