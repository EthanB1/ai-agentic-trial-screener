# tests/test_anthropic_api.py

import os
import pytest
from dotenv import load_dotenv
from unittest.mock import MagicMock
from app.services.anthropic_service import AnthropicService

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_anthropic_api():
    # Mock the app context
    mock_app = MagicMock()
    
    # Initialize AnthropicService with the mock app
    anthropic_service = AnthropicService(
        app=mock_app,
        model_name=os.getenv('ANTHROPIC_MODEL_NAME', 'claude-3-opus-20240229'),
        api_key=os.getenv('ANTHROPIC_API_KEY')
    )
    # Test messages
    messages = [
        {"role": "user", "content": "Hello, Claude. Can you hear me?"}
    ]

    try:
        # Call the API
        response = await anthropic_service.invoke_model(messages)
        
        # Check if we got a valid response
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

        print(f"Anthropic API Response: {response}")

    except Exception as e:
        pytest.fail(f"Anthropic API call failed: {str(e)}")

@pytest.mark.asyncio
async def test_match_patient_to_trials():
    # Mock the app context
    mock_app = MagicMock()
    
    # Initialize AnthropicService with the mock app
    anthropic_service = AnthropicService(
        app=mock_app,
        model_name=os.getenv('ANTHROPIC_MODEL_NAME', 'claude-3-opus-20240229'),
        api_key=os.getenv('ANTHROPIC_API_KEY')
    )

    patient_data = {
        "age": 45,
        "gender": "female",
        "conditions": ["type 2 diabetes", "hypertension"],
        "medications": ["metformin", "lisinopril"]
    }

    trials_data = [
        {
            "nct_id": "NCT12345678",
            "title": "Study of New Diabetes Treatment",
            "conditions": ["type 2 diabetes"],
            "eligibility_criteria": "Adults aged 18-65 with type 2 diabetes"
        },
        {
            "nct_id": "NCT87654321",
            "title": "Hypertension Management Study",
            "conditions": ["hypertension"],
            "eligibility_criteria": "Adults aged 40-70 with hypertension"
        }
    ]

    try:
        matches = await anthropic_service.match_patient_to_trials(patient_data, trials_data)
        
        assert isinstance(matches, list)
        assert len(matches) > 0
        for match in matches:
            assert "nct_id" in match
            assert "compatibility_score" in match
            assert "reasons" in match

        print(f"Matching results: {matches}")

    except Exception as e:
        pytest.fail(f"Match patient to trials failed: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_anthropic_api())
    asyncio.run(test_match_patient_to_trials())