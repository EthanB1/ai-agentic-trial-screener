# tests/test_proactive_search_service.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from bson import ObjectId
from flask import Flask
import asyncio

from app.services.proactive_search_service import ProactiveSearchService
from app.services.trial_matching_service import TrialMatchingService
from app.services.clinical_trials_gov_service import ClinicalTrialsGovService
from app.services.email_service import EmailService

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def mock_trial_matching_service():
    return AsyncMock(spec=TrialMatchingService)

@pytest.fixture
def mock_clinical_trials_service():
    return AsyncMock(spec=ClinicalTrialsGovService)

@pytest.fixture
def mock_email_service():
    return AsyncMock(spec=EmailService)

@pytest.fixture
def proactive_search_service(mock_trial_matching_service, mock_clinical_trials_service, mock_email_service):
    service = ProactiveSearchService(mock_trial_matching_service, mock_clinical_trials_service)
    service.email_service = mock_email_service
    return service

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_run_proactive_search(proactive_search_service, mock_db, app):
    mock_new_trials = [{"nct_id": "NCT12345678", "brief_title": "New Test Trial", "eligibility_criteria": "Adults 18-65 with diabetes"}]
    mock_patients = [
        {"_id": ObjectId(), "user_id": "test_user_1", "email": "test1@example.com", "first_name": "John", "last_name": "Doe", "medical_conditions": ["Diabetes"]},
        {"_id": ObjectId(), "user_id": "test_user_2", "email": "test2@example.com", "first_name": "Jane", "last_name": "Smith", "medical_conditions": ["Hypertension"]}
    ]
    mock_matches = [{"nct_id": "NCT12345678", "compatibility_score": 85}]

    proactive_search_service.fetch_new_trials = AsyncMock(return_value=mock_new_trials)
    proactive_search_service.process_and_save_trials = AsyncMock(return_value=mock_new_trials)
    proactive_search_service.match_trials_with_patients = AsyncMock()
    proactive_search_service.update_last_check_date = AsyncMock()

    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db):
            await proactive_search_service.run_proactive_search()

    assert proactive_search_service.fetch_new_trials.called
    assert proactive_search_service.process_and_save_trials.called
    assert proactive_search_service.match_trials_with_patients.called
    assert proactive_search_service.update_last_check_date.called

@pytest.mark.asyncio
async def test_fetch_new_trials(proactive_search_service, mock_db, app):
    mock_last_check = datetime.utcnow() - timedelta(days=1)
    mock_new_trials = [{"nct_id": "NCT12345678", "brief_title": "New Test Trial", "eligibility_criteria": "Adults 18-65 with diabetes"}]

    proactive_search_service.get_last_check_date = AsyncMock(return_value=mock_last_check)
    proactive_search_service.clinical_trials_service.fetch_trials = AsyncMock(return_value=mock_new_trials)

    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db):
            result = await proactive_search_service.fetch_new_trials()

    assert result == mock_new_trials
    proactive_search_service.get_last_check_date.assert_called_once()
    proactive_search_service.clinical_trials_service.fetch_trials.assert_called_once_with(min_date=mock_last_check)

@pytest.mark.asyncio
async def test_process_and_save_trials(proactive_search_service, mock_db, app):
    mock_trials = [{"nct_id": "NCT12345678", "brief_title": "Test Trial", "eligibility_criteria": "Adults 18-65"}]
    mock_analyzed_criteria = {"age_range": {"min": 18, "max": 65}, "gender": "All", "conditions": ["Any"]}

    proactive_search_service.trial_matching_service.analyze_eligibility_criteria = AsyncMock(return_value=mock_analyzed_criteria)
    mock_db.clinical_trials.update_one.return_value = AsyncMock(upserted_id=ObjectId())

    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db), \
             patch('app.services.proactive_search_service.sanitize_trial_data', side_effect=lambda x: x), \
             patch('app.services.proactive_search_service.sanitize_mongo_query', side_effect=lambda x: x):
            result = await proactive_search_service.process_and_save_trials(mock_trials)

    assert len(result) == 1
    assert result[0]['nct_id'] == "NCT12345678"
    assert result[0]['analyzed_criteria'] == mock_analyzed_criteria
    mock_db.clinical_trials.update_one.assert_called_once()

@pytest.mark.asyncio
async def test_match_trials_with_patients(proactive_search_service, mock_db, app):
    mock_trials = [{"nct_id": "NCT12345678", "brief_title": "Test Trial", "eligibility_criteria": "Adults 18-65"}]
    mock_patients = [{"_id": ObjectId(), "user_id": "test_user_1", "email": "test1@example.com", "medical_conditions": ["Diabetes"]}]
    mock_matches = [{"nct_id": "NCT12345678", "compatibility_score": 85}]

    class AsyncIterator:
        def __init__(self, items):
            self.items = items

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return self.items.pop(0)
            except IndexError:
                raise StopAsyncIteration

    mock_db.patients.find = AsyncMock(return_value=AsyncIterator(mock_patients))
    proactive_search_service.trial_matching_service.match_patient_to_trials = AsyncMock(return_value=mock_matches)
    proactive_search_service.notify_patient = AsyncMock()
    proactive_search_service.update_patient_matches = AsyncMock()

    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db), \
             patch('app.services.proactive_search_service.sanitize_patient_data', side_effect=lambda x: x):
            await proactive_search_service.match_trials_with_patients(mock_trials)

    # Add assertions
    proactive_search_service.trial_matching_service.match_patient_to_trials.assert_called_once()
    proactive_search_service.notify_patient.assert_called_once()
    proactive_search_service.update_patient_matches.assert_called_once()
    
@pytest.mark.asyncio
async def test_notify_patient(proactive_search_service, app, mock_db):
    mock_patient = {"_id": ObjectId(), "email": "test@example.com", "first_name": "John", "last_name": "Doe"}
    mock_matches = [{"nct_id": "NCT12345678", "brief_title": "Test Trial", "compatibility_score": 85}]

    proactive_search_service.email_service.send_trial_match_email = AsyncMock(return_value=True)
    
    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db), \
             patch('app.utils.input_sanitizer.sanitize_input', side_effect=lambda x: x):
            await proactive_search_service.notify_patient(mock_patient, mock_matches)

    proactive_search_service.email_service.send_trial_match_email.assert_called_once_with(
        "test@example.com",
        "John Doe",
        mock_matches
    )
    mock_db.patients.update_one.assert_called_once()

@pytest.mark.asyncio
async def test_update_patient_matches(proactive_search_service, mock_db, app):
    mock_patient_id = ObjectId()
    mock_matches = [{"nct_id": "NCT12345678", "compatibility_score": 85}]

    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db), \
             patch('app.services.proactive_search_service.sanitize_mongo_query', side_effect=lambda x: x):
            await proactive_search_service.update_patient_matches(mock_patient_id, mock_matches)

    mock_db.patients.update_one.assert_called_once()

@pytest.mark.asyncio
async def test_get_last_check_date(proactive_search_service, mock_db, app):
    mock_last_check = datetime.utcnow() - timedelta(days=1)
    mock_db.proactive_search_log.find_one.return_value = {"check_date": mock_last_check}

    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db):
            result = await proactive_search_service.get_last_check_date()

    assert result == mock_last_check

@pytest.mark.asyncio
async def test_update_last_check_date(proactive_search_service, mock_db, app):
    with app.app_context():
        with patch('app.services.proactive_search_service.get_db', return_value=mock_db):
            await proactive_search_service.update_last_check_date()

    mock_db.proactive_search_log.insert_one.assert_called_once()

if __name__ == '__main__':
    pytest.main()