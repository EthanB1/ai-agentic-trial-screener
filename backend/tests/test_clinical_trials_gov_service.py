# tests/test_clinical_trials_gov_service.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from bson import ObjectId
from flask import Flask
from quart.testing import QuartClient
from app.services.clinical_trials_gov_service import ClinicalTrialsGovService
from app.database import get_db
import aiohttp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def async_client(app):
    return QuartClient(app)

@pytest.fixture
def clinical_trials_service(app):
    return ClinicalTrialsGovService()

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_fetch_trials(clinical_trials_service, mock_db, app):
    mock_response_data = {
        'studies': [
            {
                'protocolSection': {
                    'identificationModule': {'nctId': 'NCT12345678'},
                    'statusModule': {'overallStatus': 'Recruiting', 'lastUpdatePostDate': '2023-06-01'},
                    'designModule': {'phases': ['Phase 2']},
                    'conditionsModule': {'conditions': ['Cancer']},
                    'descriptionModule': {
                        'briefSummary': 'A brief summary',
                        'detailedDescription': 'A detailed description'
                    },
                    'eligibilityModule': {'eligibilityCriteria': 'Adults 18-65'}
                }
            }
        ],
        'nextPageToken': 'next_page_token'
    }

    mock_response = AsyncMock()
    mock_response.__aenter__.return_value.json.return_value = mock_response_data
    mock_response.__aenter__.return_value.raise_for_status = AsyncMock()

    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        trials, next_token = await clinical_trials_service.fetch_trials()

    assert len(trials) == 1
    assert trials[0]['protocolSection']['identificationModule']['nctId'] == 'NCT12345678'
    assert next_token == 'next_page_token'

    mock_response.__aenter__.return_value.raise_for_status.assert_called_once()

@pytest.mark.asyncio
async def test_process_trials(clinical_trials_service):
    raw_trials = [
        {
            'protocolSection': {
                'identificationModule': {'nctId': 'NCT12345678', 'briefTitle': 'Test Trial', 'officialTitle': 'Official Test Trial'},
                'statusModule': {'overallStatus': 'Recruiting', 'lastUpdatePostDate': '2023-06-01'},
                'designModule': {'phases': ['Phase 2']},
                'conditionsModule': {'conditions': ['Cancer']},
                'descriptionModule': {
                    'briefSummary': 'A brief summary',
                    'detailedDescription': 'A detailed description'
                },
                'eligibilityModule': {'eligibilityCriteria': 'Adults 18-65'},
            }
        }
    ]

    processed_trials = clinical_trials_service.process_trials(raw_trials)

    assert len(processed_trials) == 1
    assert processed_trials[0]['nct_id'] == 'NCT12345678'
    assert processed_trials[0]['brief_title'] == 'Test Trial'
    assert processed_trials[0]['official_title'] == 'Official Test Trial'
    assert processed_trials[0]['status'] == 'Recruiting'
    assert processed_trials[0]['phase'] == ['Phase 2']
    assert processed_trials[0]['conditions'] == ['Cancer']
    assert processed_trials[0]['eligibility'] == 'Adults 18-65'
    assert processed_trials[0]['brief_summary'] == 'A brief summary'
    assert processed_trials[0]['detailed_description'] == 'A detailed description'
    assert processed_trials[0]['last_update_posted'] == '2023-06-01'

@pytest.mark.asyncio
async def test_save_trials(clinical_trials_service, mock_db, async_client):
    trials = [
        {
            'nct_id': 'NCT12345678',
            'brief_title': 'Test Trial',
            'official_title': 'Official Test Trial',
            'status': 'Recruiting',
            'phase': ['Phase 2'],
            'conditions': ['Cancer'],
            'eligibility': 'Adults 18-65',
            'brief_summary': 'A brief summary',
            'detailed_description': 'A detailed description',
            'last_update_posted': '2023-06-01'
        }
    ]

    mock_db.clinical_trials.update_one.return_value = AsyncMock(upserted_id=ObjectId(), modified_count=0)

    with patch('app.services.clinical_trials_gov_service.get_db', return_value=mock_db):
        saved_count, updated_count = await clinical_trials_service.save_trials(trials)

    assert saved_count == 1
    assert updated_count == 0
    mock_db.clinical_trials.update_one.assert_called_once()

@pytest.mark.asyncio
async def test_get_most_recent_trial_date(clinical_trials_service, mock_db):
    mock_recent_trial = {'last_update_posted': '2023-06-01'}
    mock_db.clinical_trials.find_one.return_value = mock_recent_trial

    with patch('app.services.clinical_trials_gov_service.get_db', return_value=mock_db):
        result = await clinical_trials_service.get_most_recent_trial_date()

    assert result == datetime(2023, 6, 1)

@pytest.mark.asyncio
async def test_fetch_and_save_trials(clinical_trials_service, mock_db):
    mock_trials = [{'nct_id': 'NCT12345678', 'brief_title': 'Test Trial'}]
    
    with patch.object(ClinicalTrialsGovService, 'fetch_trials', new_callable=AsyncMock) as mock_fetch, \
         patch.object(ClinicalTrialsGovService, 'process_trials', return_value=mock_trials) as mock_process, \
         patch.object(ClinicalTrialsGovService, 'save_trials', new_callable=AsyncMock) as mock_save, \
         patch.object(ClinicalTrialsGovService, 'get_most_recent_trial_date', new_callable=AsyncMock) as mock_get_date:
        
        mock_fetch.return_value = (mock_trials, None)
        mock_save.return_value = (1, 0)
        mock_get_date.return_value = datetime(2023, 6, 1)

        with patch('app.services.clinical_trials_gov_service.get_db', return_value=mock_db):
            total_saved, total_updated = await clinical_trials_service.fetch_and_save_trials(num_trials=1)

    assert total_saved == 1
    assert total_updated == 0
    mock_fetch.assert_called_once()
    mock_process.assert_called_once()
    mock_save.assert_called_once()

@pytest.mark.asyncio
async def test_get_database_statistics(clinical_trials_service, mock_db):
    mock_db.clinical_trials.count_documents.return_value = 100
    mock_db.clinical_trials.find_one.side_effect = [
        {'last_update_posted': '2023-01-01'},
        {'last_update_posted': '2023-06-01'}
    ]

    mock_status_results = [
        {'value': 'Recruiting', 'count': 50},
        {'value': 'Completed', 'count': 50}
    ]
    mock_phase_results = [
        {'value': 'Phase 1', 'count': 30},
        {'value': 'Phase 2', 'count': 70}
    ]

    mock_status_cursor = AsyncMock()
    mock_status_cursor.to_list.return_value = mock_status_results
    mock_phase_cursor = AsyncMock()
    mock_phase_cursor.to_list.return_value = mock_phase_results
    mock_db.clinical_trials.aggregate.side_effect = [mock_status_cursor, mock_phase_cursor]

    with patch('app.services.clinical_trials_gov_service.get_db', return_value=mock_db):
        stats = await clinical_trials_service.get_database_statistics()

    assert stats['total_trials'] == 100
    assert stats['date_range']['earliest'] == '2023-01-01'
    assert stats['date_range']['latest'] == '2023-06-01'
    assert stats['status_counts'] == {'Recruiting': 50, 'Completed': 50}
    assert stats['phase_counts'] == {'Phase 1': 30, 'Phase 2': 70}

    assert mock_db.clinical_trials.aggregate.call_count == 2

    status_call = mock_db.clinical_trials.aggregate.call_args_list[0]
    assert list(status_call.args[0]) == [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "value": "$_id", "count": 1}}
    ]

    phase_call = mock_db.clinical_trials.aggregate.call_args_list[1]
    assert list(phase_call.args[0]) == [
        {"$unwind": "$phase"},
        {"$group": {"_id": "$phase", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "value": "$_id", "count": 1}}
    ]

if __name__ == '__main__':
    pytest.main()