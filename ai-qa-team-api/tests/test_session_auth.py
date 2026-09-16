import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.responses import JSONResponse
from starlette.requests import Request


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017",
    "MONGO_DB": "auth_tests",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test-only",
    "SESSION_SECRET_KEY": "session-test-only",
    "JWT_SECRET_KEY": "jwt-test-only",
}

with patch.dict(os.environ, TEST_ENV):
    from app.models.user_model import User
    from app.routes import auth_routes
    from app.utils import auth_cookies
    from app.utils.mongo_helper import serialize_public_user


class _InsertResult:
    inserted_id = "user-1"


class _UsersCollection:
    def __init__(self, existing=None):
        self.existing = existing
        self.inserted = None

    async def find_one(self, _query):
        return self.existing

    async def insert_one(self, document):
        self.inserted = document
        return _InsertResult()


class AuthSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_signup_registers_refresh_token_and_returns_safe_user(self):
        users = _UsersCollection()
        fake_db = {"users": users}

        with (
            patch.object(auth_routes, "db", fake_db),
            patch.object(auth_routes.pwd_context, "hash", return_value="stored-password-hash"),
            patch.object(auth_routes, "create_access_token", return_value="access-token"),
            patch.object(auth_routes, "create_refresh_token", return_value="refresh-token"),
            patch.object(auth_routes, "store_refresh_token") as store_refresh,
            patch.object(auth_routes, "activate_pending_memberships", return_value=0),
        ):
            response = await auth_routes.signup(
                User(name="New User", email="new@example.com", password="secret")
            )

        store_refresh.assert_called_once_with("new@example.com", "refresh-token")
        payload = json.loads(response.body)
        self.assertEqual(payload["user"]["email"], "new@example.com")
        self.assertNotIn("password", payload["user"])
        self.assertNotIn("password_hash", payload["user"])

    async def test_login_uses_same_refresh_registration_and_safe_serializer(self):
        users = _UsersCollection(
            {
                "_id": "user-1",
                "name": "Existing User",
                "email": "existing@example.com",
                "password": "stored-password-hash",
                "password_hash": "must-not-leak",
                "provider": "local",
                "role": "admin",
            }
        )

        with (
            patch.object(auth_routes, "db", {"users": users}),
            patch.object(auth_routes.pwd_context, "verify", return_value=True),
            patch.object(auth_routes, "create_access_token", return_value="access-token"),
            patch.object(auth_routes, "create_refresh_token", return_value="refresh-token"),
            patch.object(auth_routes, "store_refresh_token") as store_refresh,
            patch.object(auth_routes, "activate_pending_memberships", return_value=0),
        ):
            response = await auth_routes.login(
                {"email": "existing@example.com", "password": "secret"}
            )

        store_refresh.assert_called_once_with("existing@example.com", "refresh-token")
        payload = json.loads(response.body)
        self.assertNotIn("password", payload["user"])
        self.assertNotIn("password_hash", payload["user"])

    def test_public_user_serializer_excludes_credentials_and_integrations(self):
        serialized = serialize_public_user(
            {
                "email": "safe@example.com",
                "password": "hash",
                "password_hash": "hash-2",
                "integrations": {"google": {"access_token": "provider-secret"}},
                "subscription": {"plan": "free"},
            }
        )

        self.assertEqual(
            serialized,
            {"email": "safe@example.com", "subscription": {"plan": "free"}},
        )

    def test_production_cookies_are_secure_and_have_explicit_lifetimes(self):
        response = JSONResponse({"ok": True})
        with patch.object(auth_cookies.settings, "app_env", "production"):
            auth_cookies.set_auth_cookies(response, "access", "refresh")

        cookies = response.headers.getlist("set-cookie")
        self.assertEqual(len(cookies), 2)
        self.assertTrue(all("HttpOnly" in cookie for cookie in cookies))
        self.assertTrue(all("; Secure" in cookie for cookie in cookies))
        self.assertTrue(all("SameSite=lax" in cookie for cookie in cookies))
        self.assertTrue(all("Path=/" in cookie for cookie in cookies))
        self.assertTrue(all("Max-Age=" in cookie and "expires=" in cookie for cookie in cookies))
        self.assertTrue(all("Domain=" not in cookie for cookie in cookies))
        self.assertIn("Max-Age=3600", cookies[0])
        self.assertIn("Max-Age=604800", cookies[1])

    def test_development_cookies_remain_usable_over_local_http(self):
        response = JSONResponse({"ok": True})
        with patch.object(auth_cookies.settings, "app_env", "development"):
            auth_cookies.set_auth_cookies(response, "access", "refresh")

        cookies = response.headers.getlist("set-cookie")
        self.assertTrue(all("; Secure" not in cookie for cookie in cookies))
        self.assertTrue(all("HttpOnly" in cookie and "SameSite=lax" in cookie for cookie in cookies))

    async def test_refresh_returns_no_token_in_json_and_renews_cookie(self):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/auth/refresh",
                "headers": [(b"cookie", b"refresh_token=existing-refresh")],
            }
        )

        with (
            patch.object(
                auth_routes,
                "decode_token",
                return_value={"email": "safe@example.com", "role": "admin"},
            ),
            patch.object(auth_routes, "get_refresh_token", return_value="existing-refresh"),
            patch.object(auth_routes, "create_access_token", return_value="new-access-token"),
        ):
            response = await auth_routes.refresh_token(request)

        self.assertEqual(json.loads(response.body), {"status": "ok"})
        self.assertNotIn("new-access-token", response.body.decode())
        self.assertIn("access_token=new-access-token", response.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()
