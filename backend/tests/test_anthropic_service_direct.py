# tests/test_anthropic_service_direct.py

import pytest
from app.services.anthropic_service import AnthropicService

def test_anthropic_service_creation():
    service = AnthropicService(model_name="test-model", api_key="test-key")
    assert isinstance(service, AnthropicService)

# Add more tests as needed