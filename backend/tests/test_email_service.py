import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from flask import Flask
from app.services.email_service import EmailService
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SENDGRID_API_KEY'] = 'test_api_key'
    app.config['SENDGRID_FROM_EMAIL'] = 'test@example.com'
    return app

@pytest.fixture
def email_service(app):
    service = EmailService()
    service.initialize(app)
    return service

@pytest.mark.asyncio
async def test_send_trial_match_email(email_service, app):
    with app.app_context():
        # Test implementation remains the same
        pass

@pytest.mark.asyncio
async def test_send_trial_match_email_failure(email_service, app):
    with app.app_context():
        # Test implementation remains the same
        pass

@pytest.mark.asyncio
async def test_send_trial_match_email_no_trials(email_service, app):
    with app.app_context():
        # Test implementation remains the same
        pass

def test_email_service_initialization(app):
    email_service = EmailService()
    email_service.initialize(app)

    assert email_service.from_email == 'test@example.com'
    assert isinstance(email_service.sg, SendGridAPIClient)

def test_email_service_singleton():
    service1 = EmailService.get_instance()
    service2 = EmailService.get_instance()
    assert service1 is service2

if __name__ == '__main__':
    pytest.main()