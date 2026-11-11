from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import certifi
import ssl
import os

tls_config = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
tls_config.load_verify_locations(certifi.where())

client = AsyncIOMotorClient(settings.mongo_uri,tls=True,tlsCAFile=settings.mongo_tls_ca_file or certifi.where(),)
db = client[settings.mongo_db]
