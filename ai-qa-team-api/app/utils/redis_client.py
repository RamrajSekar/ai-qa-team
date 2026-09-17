import threading
import time

import redis

from app.config import settings


redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    username=settings.redis_username,
    password=settings.redis_password,
    decode_responses=True,
    socket_connect_timeout=10,
)


class LocalCache(dict):
    def __init__(self):
        super().__init__()
        self._expires = {}
        self._lock = threading.Lock()

    def _purge(self, key):
        if self._expires.get(key, float("inf")) <= time.time():
            super().pop(key, None)
            self._expires.pop(key, None)

    def ping(self):
        return True

    def setex(self, key, _ttl, value):
        self[key] = value
        self._expires[key] = time.time() + _ttl

    def get(self, key, default=None):
        self._purge(key)
        return super().get(key, default)

    def delete(self, key):
        if key in self:
            del self[key]
        self._expires.pop(key, None)

    def incr(self, key):
        with self._lock:
            self._purge(key)
            value = int(super().get(key, 0)) + 1
            super().__setitem__(key, value)
            return value

    def decr(self, key):
        with self._lock:
            self._purge(key)
            value = int(super().get(key, 0)) - 1
            super().__setitem__(key, value)
            return value

    def expire(self, key, ttl):
        if key in self:
            self._expires[key] = time.time() + ttl
            return True
        return False

    def llen(self, _key):
        return 0


def check_redis_connection():
    global redis_client
    try:
        redis_client.ping()
        print("Redis connected successfully")
        print("Checking queue length...")
        redis_client.llen("test_execution_queue")
    except Exception as e:
        print(f"Using in-memory cache fallback: {e}")
        redis_client = LocalCache()


def store_refresh_token(email: str, token: str):
    redis_client.setex(f"refresh:{email}", 7 * 24 * 60 * 60, token)


def get_refresh_token(email: str):
    return redis_client.get(f"refresh:{email}")


def delete_refresh_token(email: str):
    redis_client.delete(f"refresh:{email}")
