# app/__init__.py

import logging
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .config import Config
from . import cli
from apscheduler.schedulers.background import BackgroundScheduler
from app.scheduler import init_scheduler, shutdown_scheduler
from app.services.anthropic_service import AnthropicService
from app.services.trial_matching_service import TrialMatchingService
from app.services.proactive_search_service import ProactiveSearchService
from app.services.clinical_trials_gov_service import ClinicalTrialsGovService
from app.services.email_service import email_service
from dotenv import load_dotenv
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.error_handlers import handle_general_error
from flask.json.provider import JSONProvider
from bson import ObjectId
from datetime import datetime
import json
from .mongo_client import mongo_client, reset_db_connection
from .async_helper import AsyncToSync, async_to_sync, run_async
from .utils.cors_config import configure_cors
from .utils.jwt_config import configure_jwt


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Initialize AsyncToSync
async_to_sync = AsyncToSync()

class CustomJSONProvider(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, default=self.default, **kwargs)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def create_app():
    logger.info("Initializing Flask app...")
    app = Flask(__name__)
    app.matching_tasks = {}
    logger.info("Configuring app...")
    app.config.from_object(Config)
    app.json = CustomJSONProvider(app)

    logger.info("Setting up CORS...")
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    with app.app_context():
        configure_cors(app)


    logger.info("Initializing JWT manager...")
    jwt = configure_jwt(app)

    logger.info("Setting up rate limiting...")
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["2000 per day", "500 per hour"],
        storage_uri="memory://"
    )
    limiter.init_app(app)

    logger.info("Setting up database...")
    async_to_sync.run_async(setup_db())

    @app.before_request
    async def before_request():
        try:
            app.db = await mongo_client.get_db()
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            await reset_db_connection()
            raise

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    logger.info("Registering error handler...")
    @app.errorhandler(Exception)
    def handle_exception(e):
        return handle_general_error(e)

    logger.info("Initializing CLI commands...")
    cli.init_cli(app)

    logger.info("Registering routes...")
    from .routes import register_routes
    register_routes(app)

    logger.info("Initializing services...")
    app.anthropic_service = AnthropicService(api_key=os.getenv('ANTHROPIC_API_KEY'), app=app)
    app.clinical_trials_service = ClinicalTrialsGovService()
    app.trial_matching_service = TrialMatchingService(app.anthropic_service, app.clinical_trials_service)
    app.proactive_search_service = ProactiveSearchService(app.trial_matching_service, app.clinical_trials_service)

    logger.info("Initializing email service...")
    email_service.initialize(app)

    logger.info("Setting up scheduler...")
    scheduler = BackgroundScheduler()
    app.scheduler = scheduler

    logger.info("Initializing scheduler...")
    with app.app_context():
        init_scheduler(app, app.proactive_search_service, scheduler)

    @app.teardown_appcontext
    async def cleanup(exception=None):
        shutdown_scheduler(app.scheduler)

    logger.info("Application initialized successfully")
    return app

async def setup_db():
    try:
        logger.info("Starting database setup...")
        await mongo_client.initialize()
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Error in database setup: {str(e)}")
        raise