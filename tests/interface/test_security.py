"""HTTP security boundary tests."""

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.interface.security import SecurityHeadersMiddleware, public_error


async def _ok(request):
    return PlainTextResponse("ok")


def test_security_middleware_sets_request_id_and_headers():
    app = Starlette(routes=[Route("/", _ok)], middleware=[Middleware(SecurityHeadersMiddleware)])
    response = TestClient(app).get("/", headers={"X-Request-ID": "known-request"})

    assert response.headers["x-request-id"] == "known-request"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_public_error_returns_complete_exception_text(caplog):
    request = type("Request", (), {"state": type("State", (), {"request_id": "known"})()})()
    raw = "driver failure [SQL: DROP TABLE X] [parameters: ('secret',)]"

    assert public_error(request, RuntimeError(raw), "ignored") == raw
    assert "known" in caplog.text
