import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017",
    "MONGO_DB": "cors_tests",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test-only",
    "SESSION_SECRET_KEY": "session-test-only",
    "JWT_SECRET_KEY": "jwt-test-only",
    "CORS_ORIGINS": "https://ai-qa-team.vercel.app/",
}

with patch.dict(os.environ, TEST_ENV):
    from app.main import app


class CorsPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def preflight(self, origin: str):
        return self.client.options(
            "/auth/signup",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    def test_configured_production_frontend_is_allowed(self):
        response = self.preflight("https://ai-qa-team.vercel.app")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-qa-team.vercel.app",
        )
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_existing_local_frontend_is_allowed(self):
        response = self.preflight("http://localhost:3002")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3002",
        )

    def test_unlisted_origin_is_rejected(self):
        response = self.preflight("https://untrusted.example")

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))


if __name__ == "__main__":
    unittest.main()
