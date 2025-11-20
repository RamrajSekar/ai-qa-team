# import asyncio
# from redis.asyncio import Redis
# from app.config import settings

# async def main():
#     r = Redis(
#         host=settings.redis_host,
#         port=settings.redis_port,
#         username=settings.redis_username,
#         password=settings.redis_password,
#         ssl=True,  # IMPORTANT for Redis Cloud
#         ssl_cert_reqs=None,
#         decode_responses=True
#     )

#     print("🔍 Testing connection...")
#     print(await r.ping())

#     print("🔍 Checking queue length...")
#     print(await r.llen("test_execution_queue"))

#     print("🔍 Trying BRPOP (5 sec timeout)...")
#     result = await r.brpop("test_execution_queue", timeout=5)
#     print("BRPOP Result:", result)

# asyncio.run(main())
