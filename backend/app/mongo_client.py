# app/mongo_client.py

import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
import logging
from contextvars import ContextVar
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a context variable to store the database connection
db_context = ContextVar('db_context', default=None)

class MongoClient:
    _instance = None
    _client = None
    _db = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls):
        async with cls._lock:
            if cls._client is None:
                try:
                    # Get MongoDB URI from environment variable
                    mongo_uri = os.getenv('MONGODB_URI')
                    if not mongo_uri:
                        raise ValueError("MONGODB_URI environment variable is not set")

                    # Connect to MongoDB with a connection pool
                    cls._client = AsyncIOMotorClient(mongo_uri, 
                                                     maxPoolSize=50,
                                                     minPoolSize=10,
                                                     maxIdleTimeMS=300000,  # 5 minutes
                                                     serverSelectionTimeoutMS=5000)
                    
                    # Get database name from environment variable or use default
                    db_name = os.getenv('MONGODB_DB_NAME', 'clinical_trial_screener')
                    cls._db = cls._client[db_name]

                    # Verify connection
                    await cls._client.server_info()
                    logger.info(f"Connected to MongoDB database: {db_name}")
                except Exception as e:
                    logger.error(f"Failed to connect to MongoDB: {str(e)}")
                    raise

    @classmethod
    async def get_db(cls):
        if cls._db is None:
            await cls.initialize()
        return cls._db

    @classmethod
    async def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("MongoDB connection closed")

# Create a global instance of MongoClient
mongo_client = MongoClient()

async def get_db():
    db = db_context.get()
    if db is None:
        db = await mongo_client.get_db()
        db_context.set(db)
    return db

# Add a new function to reset the database connection
async def reset_db_connection():
    await mongo_client.close()
    await mongo_client.initialize()
    logger.info("MongoDB connection reset")