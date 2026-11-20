"""Isolated auth/token/reference regressions; no external service calls."""
import asyncio
import threading
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from test_session_auth import auth_routes, _UsersCollection, User
from app.utils import jwt_handler, auth_dependency
from app.utils.account_references import authorize_references


def request(body=None):
    import json
    payload = json.dumps(body or {}).encode()
    async def receive(): return {"type": "http.request", "body": payload}
    return Request({"type": "http", "method": "POST", "path": "/batch", "headers": [(b"content-type", b"application/json")], "query_string": b""}, receive)


class TokenPurposeTests(unittest.TestCase):
    def test_refresh_tokens_cannot_authenticate_access_requests(self):
        token = jwt_handler.create_refresh_token({"email": "fixture@example.com"})
        with self.assertRaises(jwt.InvalidTokenError): jwt_handler.decode_token(token)
        self.assertEqual(jwt_handler.decode_token(token, "refresh")["type"], "refresh")

    def test_access_tokens_cannot_be_used_as_refresh_tokens(self):
        token = jwt_handler.create_access_token({"email": "fixture@example.com"})
        self.assertEqual(jwt_handler.decode_token(token)["type"], "access")
        with self.assertRaises(jwt.InvalidTokenError): jwt_handler.decode_token(token, "refresh")

    def test_missing_expiry_and_legacy_untyped_tokens_fail_closed(self):
        for payload in ({"email": "fixture@example.com", "type": "access"},
                        {"email": "fixture@example.com", "exp": datetime.now(timezone.utc)+timedelta(minutes=1)}):
            token = jwt.encode(payload, jwt_handler.SECRET_KEY, algorithm=jwt_handler.ALGORITHM)
            with self.assertRaises(jwt.InvalidTokenError): jwt_handler.decode_token(token)


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def test_password_verification_does_not_block_event_loop(self):
        started, release = threading.Event(), threading.Event()
        def held_verify(*args):
            started.set()
            release.wait(3)
            return False
        users = _UsersCollection({"password": "fixture-hash"})
        with patch.object(auth_routes, "db", {"users": users}), patch.object(auth_routes.pwd_context, "verify", side_effect=held_verify):
            task = asyncio.create_task(auth_routes.login({"email": "fixture@example.com", "password": "fixture"}))
            try:
                for _ in range(100):
                    if started.is_set(): break
                    await asyncio.sleep(.01)
                self.assertTrue(started.is_set())
                self.assertFalse(task.done(), "bcrypt must not hold the event loop")
            finally:
                release.set()
            with self.assertRaises(HTTPException) as error: await task
            self.assertEqual(error.exception.status_code, 401)

    async def test_refresh_cookie_is_rejected_on_both_access_paths(self):
        token = jwt_handler.create_refresh_token({"email": "fixture@example.com"})
        req = Request({"type": "http", "headers": [(b"cookie", f"access_token={token}".encode())]})
        with patch.object(auth_dependency, "db", {}), patch.object(auth_routes, "db", {}):
            for endpoint in (auth_dependency.get_current_user, auth_routes.get_my_profile):
                with self.assertRaises(HTTPException) as error: await endpoint(req)
                self.assertEqual(error.exception.status_code, 401)

    async def test_access_cookie_cannot_refresh_session(self):
        token = jwt_handler.create_access_token({"email": "fixture@example.com"})
        req = Request({"type": "http", "headers": [(b"cookie", f"refresh_token={token}".encode())]})
        with patch.object(auth_routes, "get_refresh_token") as store:
            with self.assertRaises(HTTPException) as error: await auth_routes.refresh_token(req)
            self.assertEqual(error.exception.status_code, 401)
            store.assert_not_called()

    async def test_refresh_store_wait_does_not_block_event_loop(self):
        started, release = threading.Event(), threading.Event()
        token = jwt_handler.create_refresh_token({"email": "fixture@example.com"})
        req = Request({"type": "http", "headers": [(b"cookie", f"refresh_token={token}".encode())]})
        def held_read(*args):
            started.set(); release.wait(3); return None
        with patch.object(auth_routes, "get_refresh_token", side_effect=held_read):
            task = asyncio.create_task(auth_routes.refresh_token(req))
            try:
                for _ in range(100):
                    if started.is_set(): break
                    await asyncio.sleep(.01)
                self.assertTrue(started.is_set())
                self.assertFalse(task.done())
            finally:
                release.set()
            with self.assertRaises(HTTPException) as error: await task
            self.assertEqual(error.exception.status_code, 401)

    async def test_oauth_only_account_returns_invalid_credentials(self):
        with patch.object(auth_routes, "db", {"users": _UsersCollection({"provider": "google"})}):
            with self.assertRaises(HTTPException) as error:
                await auth_routes.login({"email": "fixture@example.com", "password": "fixture"})
            self.assertEqual(error.exception.status_code, 401)

    async def test_signup_missing_password_rejected_before_any_database_call(self):
        with patch.object(auth_routes, "db", {}) as unused:
            with self.assertRaises(HTTPException) as error:
                await auth_routes.signup(User(name="Fixture", email="fixture@example.com"))
            self.assertEqual(error.exception.status_code, 422)

    def test_invalid_login_does_not_echo_sensitive_input(self):
        app = FastAPI(); app.include_router(auth_routes.router)
        with TestClient(app) as client:
            for payload in ({"email": "fixture@example.com", "password": {"secret": "never-echo"}}, {"password": "never-echo"}):
                response = client.post('/auth/login', json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn("never-echo", response.text)


class ReferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_oversized_list_rejected_before_database_work(self):
        with self.assertRaises(HTTPException) as error:
            await authorize_references(request({"testcase_ids": ["T"]*1001}), {}, {})
        self.assertEqual(error.exception.status_code, 422)

    async def test_repeated_ids_at_guard_limit_use_one_lookup(self):
        collection = MagicMock()
        collection.find_one = AsyncMock(return_value={"project_id": "A"})
        guard = AsyncMock()
        with patch('app.utils.project_authorization.require_project_member', guard):
            await authorize_references(request({"testcase_ids": ["T1"]*1000}), {}, {"testcases": collection})
        collection.find_one.assert_awaited_once_with({"testcase_id": "T1"}, {"project_id": 1})
        guard.assert_awaited_once_with("A", {})

    async def test_batch_lookup_deduplicates_and_checks_every_project(self):
        collection = MagicMock()
        collection.aggregate = None
        collection.find.return_value.to_list = AsyncMock(return_value=[{"project_id": "A"}, {"project_id": "B"}])
        guard = AsyncMock(side_effect=[None, HTTPException(403, "Denied")])
        with patch('app.utils.project_authorization.require_project_member', guard):
            with self.assertRaises(HTTPException):
                await authorize_references(request({"testcase_ids": ["T1", "T1", "T2"]}), {}, {"testcases": collection})
        self.assertEqual(guard.await_count, 2)
        collection.find.assert_called_once_with({"testcase_id": {"$in": ["T1", "T2"]}}, {"project_id": 1})
        collection.find.return_value.to_list.assert_awaited_once_with(2)
