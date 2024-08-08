from motor.motor_asyncio import AsyncIOMotorClient
import traceback
from flask import current_app, g
import logging
from pymongo import IndexModel, ASCENDING, TEXT
import asyncio
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

async def get_db():
    if 'db' not in g:
        try:
            logger.info("Attempting to establish database connection...")
            client = AsyncIOMotorClient(current_app.config['MONGODB_URI'], serverSelectionTimeoutMS=5000)
            await asyncio.wait_for(client.server_info(), timeout=10.0)  # 10 seconds timeout
            logger.info("Database connection established successfully")
            g.db = client[current_app.config['MONGODB_DB_NAME']]
            g.mongo_client = client
        except asyncio.TimeoutError:
            logger.error("Timeout while connecting to the database")
            raise RuntimeError("Database connection timeout")
        except Exception as e:
            logger.error(f"Failed to establish database connection: {str(e)}")
            raise RuntimeError("Failed to connect to the database") from e
    return g.db

async def close_db(e=None):
    db = g.pop('db', None)
    mongo_client = g.pop('mongo_client', None)
    if mongo_client is not None:
        mongo_client.close()
        logger.info("Database connection closed")

async def create_indexes(db):
    try:
        await db.clinical_trials.create_indexes([
            IndexModel([("nct_id", ASCENDING)], unique=True),
            IndexModel([("last_update_posted", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("phase", ASCENDING)]),
            IndexModel([("conditions", TEXT)])
        ])

        await db.patients.create_indexes([
            IndexModel([("user_id", ASCENDING)], unique=True),
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("medical_conditions", TEXT)]),
            IndexModel([("last_notified", ASCENDING)])
        ])

        await db.proactive_search_log.create_index("check_date")

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating database indexes: {str(e)}")
        raise RuntimeError("Failed to create database indexes") from e

async def connect_with_retry(uri):
    client = AsyncIOMotorClient(
        uri,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        retryWrites=True,
        w="majority"
    )
    await client.server_info()  # Trigger exception if can't connect
    return client

async def init_db(app):
    logger.info(f"Initializing database with URI: {app.config['MONGODB_URI']}")
    try:
        client = await connect_with_retry(app.config['MONGODB_URI'])
        db = client[app.config['MONGODB_DB_NAME']]

        collections = ['users', 'patients', 'clinical_trials', 'trial_matches', 'proactive_search_log']
        existing_collections = await db.list_collection_names()
        for collection in collections:
            if collection not in existing_collections:
                logger.info(f"Creating collection: {collection}")
                await db.create_collection(collection)
                logger.info(f"Created collection: {collection}")

        logger.info("Creating indexes...")
        await create_indexes(db)

        logger.info("Database initialized successfully")

    except asyncio.TimeoutError:
        logger.error("Timeout occurred while connecting to the database")
        raise RuntimeError("Database connection timeout")

    except ConnectionFailure as cf:
        logger.error(f"Failed to connect to the database: {str(cf)}")
        raise RuntimeError("Database connection failure")

    except ServerSelectionTimeoutError as sste:
        logger.error(f"Server selection timed out: {str(sste)}")
        raise RuntimeError("Server selection timeout")

    except Exception as e:
        logger.error(f"An unexpected error occurred during database initialization: {str(e)}")
        raise RuntimeError("Failed to initialize database") from e
