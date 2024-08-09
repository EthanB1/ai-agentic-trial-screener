# app/tasks.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging
from datetime import datetime
from app.services.proactive_search_service import ProactiveSearchService
from app.config import Config

logger = logging.getLogger(__name__)

def create_scheduler(app):
    """
    Create and configure the task scheduler.

    Args:
        app: The Flask application instance.

    Returns:
        AsyncIOScheduler: Configured scheduler instance.
    """
    scheduler = AsyncIOScheduler()
    
    # Only start scheduler if not in CLI context
    if 'flask' not in sys.argv[0].lower():
        scheduler.start()
        logger.info("Scheduler started")
    
    return scheduler

def schedule_proactive_search(scheduler, proactive_search_service):
    """
    Schedule the proactive search task.

    Args:
        scheduler (AsyncIOScheduler): The scheduler instance.
        proactive_search_service (ProactiveSearchService): The proactive search service instance.
    """
    @scheduler.scheduled_job('cron', hour=2, minute=0)  # Run daily at 2:00 AM
    async def run_proactive_search():
        """
        Wrapper function to run the proactive search asynchronously.
        """
        logger.info("Starting scheduled proactive search")
        try:
            await proactive_search_service.run_proactive_search()
            logger.info("Scheduled proactive search completed successfully")
        except Exception as e:
            logger.error(f"Error in scheduled proactive search: {str(e)}")

    logger.info("Proactive search task scheduled")

def init_scheduler(app):
    """
    Initialize the scheduler and schedule tasks.

    Args:
        app: The Flask application instance.
    """
    scheduler = create_scheduler(app)
    
    # Retrieve the ProactiveSearchService instance
    proactive_search_service = app.proactive_search_service
    
    # Schedule the proactive search task
    schedule_proactive_search(scheduler, proactive_search_service)
    
    # Add the scheduler to the app context
    app.scheduler = scheduler

    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        """
        Shut down the scheduler when the application context tears down.
        """
        if hasattr(app, 'scheduler'):
            app.scheduler.shutdown()
            logger.info("Scheduler shut down")

    logger.info("Scheduler initialized and tasks scheduled")