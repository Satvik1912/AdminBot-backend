from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "admin_db"

client = AsyncIOMotorClient(MONGO_URL)
database = client[DB_NAME]
admin_collection = database.get_collection("admins")
from pymongo import MongoClient
from app.core.config import config  

# Initialize MongoDB connection
mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.MONGO_DB_NAME]

# Ensure OTP collection is defined
otp_collection = db["otp"]