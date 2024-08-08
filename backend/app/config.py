# app/config.py

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Basic configuration
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

    CORS_ALLOWED_ORIGINS = ['http://localhost:3000']

    # Database configuration
    MONGODB_URI = os.environ.get('MONGODB_URI')
    MONGODB_DB_NAME = os.environ.get('MONGODB_DB_NAME', 'clinical_trial_screener')

    # API Keys
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    # Email configuration
    SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@yourdomain.com')

    # Anthropic model configuration
    ANTHROPIC_MODEL_NAME = os.environ.get('ANTHROPIC_MODEL_NAME', 'claude-3-sonnet-20240229')

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Rate limiting
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', "200 per day;50 per hour;1 per second")

    # Security headers
    SECURE_HEADERS = {
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'X-Content-Type-Options': 'nosniff',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; form-action 'self';"
    }

    # CORS configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

    # Scheduler configuration
    SCHEDULER_API_ENABLED = False
    SCHEDULER_TIMEZONE = "UTC"

    @classmethod
    def init_app(cls, app):
        # Validate required environment variables
        required_vars = ['SECRET_KEY', 'MONGODB_URI', 'JWT_SECRET_KEY', 'ANTHROPIC_API_KEY', 'SENDGRID_API_KEY']
        for var in required_vars:
            if not os.environ.get(var):
                raise ValueError(f"Missing required environment variable: {var}")

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    MONGODB_DB_NAME = 'clinical_trial_screener_test'

class ProductionConfig(Config):
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Log to syslog in production
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}