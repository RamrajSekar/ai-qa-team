from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import certifi
import ssl
import os

tls_config = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
tls_config.load_verify_locations(certifi.where())

client = AsyncIOMotorClient(settings.mongo_uri,tls=True,tlsCAFile=certifi.where(),)
db = client[settings.mongo_db]
