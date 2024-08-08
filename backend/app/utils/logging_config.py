# app/utils/logging_config.py

import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name, log_file, level=logging.INFO):
    """Function to set up a logger with both file and console handlers"""
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create file handler
    file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)  # 10MB per file, keep 5 old logs
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Create main application logger
app_logger = setup_logger('app', 'logs/app.log')

# Create trial matching logger
trial_matching_logger = setup_logger('trial_matching', 'logs/trial_matching.log')

# Create database logger
db_logger = setup_logger('database', 'logs/database.log')

def get_logger(name):
    if name == 'app':
        return app_logger
    elif name == 'trial_matching':
        return trial_matching_logger
    elif name == 'database':
        return db_logger
    else:
        return logging.getLogger(name)