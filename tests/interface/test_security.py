"""HTTP security boundary tests."""

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.interface.security import SecurityHeadersMiddleware


async def _ok(request):
    return PlainTextResponse("ok")


def test_security_middleware_sets_request_id_and_headers():
    app = Starlette(routes=[Route("/", _ok)], middleware=[Middleware(SecurityHeadersMiddleware)])
    response = TestClient(app).get("/", headers={"X-Request-ID": "known-request"})

    assert response.headers["x-request-id"] == "known-request"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
