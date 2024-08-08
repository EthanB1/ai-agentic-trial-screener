# test_mongo_connection.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connection():
    uri = "mongodb+srv://ethan:QtaTkpM4eSrzvjHE@cluster0.wmf5j4s.mongodb.net/clinical_trial_screener?retryWrites=true&w=majority&appName=Cluster0"
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    try:
        await client.server_info()
        print("Successfully connected to MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
    finally:
        client.close()

asyncio.run(test_connection())