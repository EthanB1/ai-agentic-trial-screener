# app/scheduler.py

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

def init_scheduler(app, proactive_search_service, scheduler):
    @scheduler.scheduled_job(CronTrigger(hour=2))  # Run every day at 2 AM
    def scheduled_proactive_search():
        app.app_context().push()  # Ensure app context is available
        asyncio.create_task(proactive_search_service.run_proactive_search())

    logger.info("Scheduler initialized")

def shutdown_scheduler(scheduler):
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")