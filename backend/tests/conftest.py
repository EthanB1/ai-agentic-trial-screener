# tests/conftest.py

import pytest
from app import create_app
from app.database import init_db, get_db
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    return create_app('testing')

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()