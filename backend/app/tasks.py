# app/tasks.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import sys

def create_scheduler(app):
    scheduler = AsyncIOScheduler()
    if 'flask' not in sys.argv[0].lower():  # Only start scheduler if not in CLI context
        scheduler.start()
        app.logger.info("Scheduler started")
    return scheduler

def schedule_proactive_search(scheduler, proactive_search_service):
    scheduler.add_job(
        func=asyncio.run,
        args=(proactive_search_service.run_proactive_search(),),
        trigger="interval",
        hours=12
    )