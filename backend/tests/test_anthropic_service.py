# tests/test_anthropic_service.py

import pytest
import json
from unittest.mock import AsyncMock, patch
from app.services.anthropic_service import AnthropicService

@pytest.fixture
def anthropic_service():
    return AnthropicService(model_name="claude-3-sonnet-20240229", api_key="test-api-key")

@pytest.mark.asyncio
async def test_analyze_eligibility_criteria_success(anthropic_service):
    mock_response = json.dumps({
        "inclusion_criteria": [
            {"category": "Age", "description": "18 years and older"}
        ],
        "exclusion_criteria": [
            {"category": "Health Condition", "description": "Active cancer"}
        ],
        "age_range": {"min": "18", "max": None, "description": "18 years and older"},
        "gender": "All",
        "health_conditions": [
            {"condition": "Diabetes", "required": True}
        ],
        "other_requirements": [
            "Able to provide informed consent"
        ]
    })

    with patch.object(anthropic_service, 'invoke_model', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_response
        result = await anthropic_service.analyze_eligibility_criteria_without_retry("Sample criteria text")

    assert 'inclusion_criteria' in result
    assert 'exclusion_criteria' in result
    assert 'age_range' in result
    assert 'gender' in result
    assert 'health_conditions' in result
    assert 'other_requirements' in result
    assert result['inclusion_criteria'][0]['category'] == 'Age'
    assert result['health_conditions'][0]['condition'] == 'Diabetes'

@pytest.mark.asyncio
async def test_analyze_eligibility_criteria_invalid_json(anthropic_service):
    with patch.object(anthropic_service, 'invoke_model', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = 'Invalid JSON'
        with pytest.raises(RuntimeError, match="Failed to parse AI response as JSON"):
            await anthropic_service.analyze_eligibility_criteria_without_retry("Sample criteria text")

@pytest.mark.asyncio
async def test_analyze_eligibility_criteria_missing_fields(anthropic_service):
    mock_response = json.dumps({"inclusion_criteria": []})
    
    with patch.object(anthropic_service, 'invoke_model', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_response
        with pytest.raises(RuntimeError, match="AI response is missing expected fields"):
            await anthropic_service.analyze_eligibility_criteria_without_retry("Sample criteria text")

@pytest.mark.asyncio
async def test_analyze_eligibility_criteria_api_error(anthropic_service):
    with patch.object(anthropic_service, 'invoke_model', side_effect=Exception("API Error")):
        with pytest.raises(RuntimeError, match="Failed to analyze eligibility criteria"):
            await anthropic_service.analyze_eligibility_criteria_without_retry("Sample criteria text")

@pytest.mark.asyncio
async def test_invoke_model(anthropic_service):
    mock_completion = AsyncMock()
    mock_completion.completion = "Mocked response"
    
    with patch.object(anthropic_service.model.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_completion
        result = await anthropic_service.invoke_model("Test prompt")

    assert result == "Mocked response"
    mock_create.assert_called_once_with(
        model=anthropic_service.model_name,
        prompt="Test prompt",
        max_tokens_to_sample=1000,
    )

@pytest.mark.asyncio
async def test_analyze_eligibility_criteria_invalid_structure(anthropic_service):
    mock_response = json.dumps({
        "inclusion_criteria": [],
        "exclusion_criteria": [],
        "age_range": "Invalid",  # This should be a dict
        "gender": "All",
        "health_conditions": [],
        "other_requirements": []
    })
    
    with patch.object(anthropic_service, 'invoke_model', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_response
        with pytest.raises(RuntimeError, match="Invalid data structure in AI response"):
            await anthropic_service.analyze_eligibility_criteria_without_retry("Sample criteria text")

if __name__ == "__main__":
    pytest.main()