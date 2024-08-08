# app/utils/resource_monitor.py

import psutil
import logging

logger = logging.getLogger(__name__)

def log_resource_usage():
    cpu_percent = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    
    logger.info(f"CPU Usage: {cpu_percent}%")
    logger.info(f"Memory Usage: {memory_info.percent}%")
    logger.info(f"Available Memory: {memory_info.available / (1024 * 1024):.2f} MB")

# Call this function at key points in your matching process