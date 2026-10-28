import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

PROD_ORIGIN = "https://2d-layoutfrontend.vercel.app"
PREVIEW_ORIGIN = "https://2d-layoutfrontend-git-main-jayyede93-7431s-projects.vercel.app"
DYNAMIC_PREVIEW_1 = "https://2d-layoutfrontend-pr-10-jayyede93-7431s-projects.vercel.app"
DYNAMIC_PREVIEW_2 = "https://2d-layoutfrontend-preview-feature.vercel.app"
LOCAL_ORIGIN = "http://localhost:5173"
LAN_ORIGIN = "http://192.168.29.238:5173"

DISALLOWED_ORIGINS = [
    "https://evil-hacker.com",
    "https://arbitrary-project.vercel.app",
    "https://evil-2d-layoutfrontend.vercel.app",
    "https://2d-layoutfrontend.evil.com",
    "http://localhost.evil.com",
]


class TestCORSPreflight:
    """Tests OPTIONS preflight requests for allowed and disallowed origins."""

    @pytest.mark.parametrize("origin", [PROD_ORIGIN, PREVIEW_ORIGIN, DYNAMIC_PREVIEW_1, DYNAMIC_PREVIEW_2, LOCAL_ORIGIN, LAN_ORIGIN])
    def test_preflight_surveys_post_allowed_origins(self, origin):
        response = client.options(
            "/api/surveys",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert "POST" in response.headers.get("access-control-allow-methods", "")
        assert "content-type" in response.headers.get("access-control-allow-headers", "").lower()
        assert response.headers.get("access-control-max-age") == "86400"

    @pytest.mark.parametrize("origin", [PROD_ORIGIN, PREVIEW_ORIGIN, LOCAL_ORIGIN])
    def test_preflight_products_get_allowed_origins(self, origin):
        response = client.options(
            "/api/products",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert "GET" in response.headers.get("access-control-allow-methods", "")

    @pytest.mark.parametrize("evil_origin", DISALLOWED_ORIGINS)
    def test_preflight_disallowed_origins(self, evil_origin):
        response = client.options(
            "/api/surveys",
            headers={
                "Origin": evil_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


class TestCORSSimpleRequests:
    """Tests GET/POST simple requests and headers."""

    @pytest.mark.parametrize("origin", [PROD_ORIGIN, PREVIEW_ORIGIN, LOCAL_ORIGIN])
    def test_get_health_allowed_origins(self, origin):
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"

    @pytest.mark.parametrize("evil_origin", DISALLOWED_ORIGINS)
    def test_get_health_disallowed_origins(self, evil_origin):
        response = client.get("/health", headers={"Origin": evil_origin})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_cors_preserved_on_404(self):
        """Verifies that 404 responses still include CORS headers for allowed origins."""
        response = client.get("/api/non-existent-endpoint-test", headers={"Origin": PROD_ORIGIN})
        assert response.status_code == 404
        assert response.headers.get("access-control-allow-origin") == PROD_ORIGIN
