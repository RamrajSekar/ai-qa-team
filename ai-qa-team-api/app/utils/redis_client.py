import redis
from app.config import settings

redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            username=settings.redis_username,
            password=settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=10
        )

def check_redis_connection():
    global redis_client
    try:
        redis_client.ping()
        print("✅ Redis connected successfully!")
        print("🔍 Checking queue length...")
        redis_client.llen("test_execution_queue")
    except Exception as e:
        print(f"⚙️ Using in-memory cache fallback: {e}")
        class LocalCache(dict):
            def ping(self): return True
        redis_client = LocalCache()

def store_refresh_token(email: str, token: str):
    # Token expires in 7 days
    redis_client.setex(f"refresh:{email}", 7 * 24 * 60 * 60, token)

def get_refresh_token(email: str):
    return redis_client.get(f"refresh:{email}")

def delete_refresh_token(email: str):
    redis_client.delete(f"refresh:{email}")

# print(check_redis_connection())