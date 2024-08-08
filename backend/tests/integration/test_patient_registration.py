# tests/integration/test_patient_registration.py

import pytest
from quart.testing import QuartClient
from app import create_app
from app.database import init_db, get_db
from app.models.user import User
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.mark.asyncio
async def test_user_registration(app, client):
    """Test user registration process."""
    async with app.app_context():
        await init_db(app)
        
        # Clear the database before test
        db_client = AsyncIOMotorClient(app.config['MONGODB_URI'])
        await db_client.drop_database(app.config['MONGODB_DB_NAME'])

        # Prepare test data
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123"
        }
    
        # Send registration request
        async with client.post('/api/auth/register', json=user_data) as response:
            # Check response
            assert response.status_code == 201
            data = await response.get_json()
            assert "message" in data
            assert "user_id" in data
    
        # Verify user was created in database
        db = await get_db()
        user = await db.users.find_one({"email": user_data["email"]})
        assert user is not None
        assert user["username"] == user_data["username"]
        
        # Test password hashing
        user_model = await User.get_user_by_email(user_data["email"])
        assert await user_model.check_password(user_data["password"])

@pytest.mark.asyncio
async def test_patient_profile_creation(app, client):
    """Test patient profile creation."""
    async with app.app_context():
        await init_db(app)
        
        # Clear the database before test
        db_client = AsyncIOMotorClient(app.config['MONGODB_URI'])
        await db_client.drop_database(app.config['MONGODB_DB_NAME'])

        # First, register a user
        user_data = {
            "username": "patientuser",
            "email": "patient@example.com",
            "password": "patientpass123"
        }
        async with client.post('/api/auth/register', json=user_data) as response:
            assert response.status_code == 201

        # Log in to get JWT token
        async with client.post('/api/auth/login', json={
            "email": user_data["email"],
            "password": user_data["password"]
        }) as login_response:
            token = (await login_response.get_json())['access_token']

        # Create patient profile
        patient_data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "medical_conditions": ["Diabetes", "Hypertension"],
            "medications": ["Metformin", "Lisinopril"]
        }
        headers = {'Authorization': f'Bearer {token}'}
        async with client.post('/api/patient/profile', json=patient_data, headers=headers) as response:
            # Check response
            assert response.status_code == 201
            data = await response.get_json()
            assert "message" in data
            assert "patient_id" in data
    
        # Verify patient profile was created in database
        db = await get_db()
        patient = await db.patients.find_one({"user_id": data["patient_id"]})
        assert patient is not None
        assert patient["first_name"] == patient_data["first_name"]
        assert patient["last_name"] == patient_data["last_name"]
        assert patient["medical_conditions"] == patient_data["medical_conditions"]

# Add more tests for profile updating, input sanitization, etc.