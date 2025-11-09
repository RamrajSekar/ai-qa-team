import redis
from app.config import settings

# redis_client = redis.from_url(settings.redis_url, socket_connect_timeout=10)

def check_redis_connection():
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            username=settings.redis_username,
            password=settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=10
        )
        redis_client.ping()
        print("✅ Redis connected successfully!")
    except Exception as e:
        print(f"⚙️ Using in-memory cache fallback: {e}")
        class LocalCache(dict):
            def ping(self): return True
        redis_client = LocalCache()