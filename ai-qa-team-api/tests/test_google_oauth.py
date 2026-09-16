import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.requests import Request


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017",
    "MONGO_DB": "oauth_tests",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test-only",
    "SESSION_SECRET_KEY": "session-test-only",
    "JWT_SECRET_KEY": "jwt-test-only",
    "GOOGLE_CLIENT_ID": "google-client-test-only",
    "GOOGLE_CLIENT_SECRET": "google-secret-test-only",
}

with patch.dict(os.environ, TEST_ENV):
    from app.routes import auth_routes
    from app.utils import auth_cookies, oauth_client


def request(path: str, query_string: bytes = b"") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "server": ("ai-qa-team.onrender.com", 443),
            "path": path,
            "query_string": query_string,
            "headers": [(b"host", b"ai-qa-team.onrender.com")],
        }
    )


class _OAuthClient:
    def __init__(self, token=None):
        self.redirect_uri = None
        self.token = token

    async def authorize_redirect(self, _request, redirect_uri):
        self.redirect_uri = str(redirect_uri)
        return MagicMock(status_code=302)

    async def authorize_access_token(self, _request):
        return self.token


class _Users:
    def __init__(self, existing):
        self.existing = existing
        self.updated = None

    async def find_one(self, _query):
        return self.existing

    async def update_one(self, query, update):
        self.updated = (query, update)
        return MagicMock()

    async def insert_one(self, document):
        self.existing = document
        return MagicMock(inserted_id="new-google-user")


class GoogleOAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_login_uses_configured_callback_not_render_host_or_override(self):
        client = _OAuthClient()
        configured = "https://ai-qa-team.vercel.app/api/auth/google/callback"

        with (
            patch.object(auth_routes.oauth, "create_client", return_value=client),
            patch.object(auth_routes.settings, "google_redirect_uri", configured),
        ):
            await auth_routes.oauth_login(
                request(
                    "/auth/google/login",
                    b"callback=https%3A%2F%2Fevil.example%2Fcallback",
                ),
                "google",
            )

        self.assertEqual(client.redirect_uri, configured)
        self.assertNotIn("onrender.com", client.redirect_uri)
        self.assertNotIn("evil.example", client.redirect_uri)

    async def test_local_google_callback_remains_environment_configurable(self):
        client = _OAuthClient()
        configured = "http://localhost:3002/api/auth/google/callback"

        with (
            patch.object(auth_routes.oauth, "create_client", return_value=client),
            patch.object(auth_routes.settings, "google_redirect_uri", configured),
        ):
            await auth_routes.oauth_login(request("/auth/google/login"), "google")

        self.assertEqual(client.redirect_uri, configured)

    async def test_callback_uses_persisted_role_redis_and_server_side_cookies(self):
        token = {
            "access_token": "google-provider-token",
            "userinfo": {"email": "admin@example.com", "name": "Admin"},
        }
        client = _OAuthClient(token)
        users = _Users(
            {
                "email": "admin@example.com",
                "name": "Admin",
                "role": "admin",
                "subscription": {"plan": "free"},
                "onboarding": {"onboarding_status": "completed"},
            }
        )
        access = MagicMock(return_value="application-access-token")
        refresh = MagicMock(return_value="application-refresh-token")

        with (
            patch.object(auth_routes.oauth, "create_client", return_value=client),
            patch.object(auth_routes, "db", {"users": users}),
            patch.object(auth_routes, "create_access_token", access),
            patch.object(auth_routes, "create_refresh_token", refresh),
            patch.object(auth_routes, "store_refresh_token") as store_refresh,
            patch.object(auth_routes.settings, "frontend_url", "https://ai-qa-team.vercel.app/"),
            patch.object(auth_routes.settings, "app_env", "production"),
        ):
            response = await auth_routes.oauth_callback(
                request("/auth/google/callback"), "google"
            )

        expected_claims = {"email": "admin@example.com", "role": "admin"}
        access.assert_called_once_with(expected_claims)
        refresh.assert_called_once_with(expected_claims)
        store_refresh.assert_called_once_with(
            "admin@example.com", "application-refresh-token"
        )
        self.assertEqual(
            response.headers["location"], "https://ai-qa-team.vercel.app/dashboard"
        )
        self.assertNotIn("application-access-token", response.headers["location"])
        self.assertNotIn("application-refresh-token", response.headers["location"])
        self.assertNotIn("admin@example.com", response.headers["location"])

        cookies = response.headers.getlist("set-cookie")
        self.assertEqual(len(cookies), 2)
        self.assertTrue(all("HttpOnly" in cookie for cookie in cookies))
        self.assertTrue(all("; Secure" in cookie for cookie in cookies))
        self.assertTrue(all("SameSite=lax" in cookie for cookie in cookies))

    async def test_new_google_user_keeps_existing_default_tester_role(self):
        client = _OAuthClient(
            {
                "access_token": "google-provider-token",
                "userinfo": {
                    "id": "google-user-1",
                    "email": "new-google@example.com",
                    "name": "New Google User",
                },
            }
        )
        users = _Users(None)
        access = MagicMock(return_value="application-access-token")

        with (
            patch.object(auth_routes.oauth, "create_client", return_value=client),
            patch.object(auth_routes, "db", {"users": users}),
            patch.object(auth_routes, "create_access_token", access),
            patch.object(
                auth_routes,
                "create_refresh_token",
                return_value="application-refresh-token",
            ),
            patch.object(auth_routes, "store_refresh_token"),
            patch.object(auth_routes.settings, "frontend_url", "http://localhost:3002"),
        ):
            await auth_routes.oauth_callback(request("/auth/google/callback"), "google")

        access.assert_called_once_with(
            {"email": "new-google@example.com", "role": "tester"}
        )

    def test_routes_use_the_single_configured_oauth_registry(self):
        self.assertIs(auth_routes.oauth, oauth_client.oauth)

    def test_oauth_state_cookie_is_secure_only_in_production(self):
        with patch.object(auth_cookies.settings, "app_env", "production"):
            self.assertEqual(
                auth_cookies.session_cookie_options(),
                {"https_only": True, "same_site": "lax"},
            )
        with patch.object(auth_cookies.settings, "app_env", "development"):
            self.assertEqual(
                auth_cookies.session_cookie_options(),
                {"https_only": False, "same_site": "lax"},
            )


if __name__ == "__main__":
    unittest.main()
