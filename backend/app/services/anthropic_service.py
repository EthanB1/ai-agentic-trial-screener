# app/services/anthropic_service.py

import json
import logging
import re
import asyncio
from typing import Dict, Any, List, Union
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.logging_config import get_logger
from app.utils.error_handlers import handle_anthropic_error
from app.utils.json_encoder import JSONEncoder
from app.utils.json_utils import sanitize_for_json
from app.utils.json_encoder import json_serialize

logger = get_logger(__name__)

class AnthropicService:
    def __init__(self, api_key: str, app):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model_name = "claude-3-5-sonnet-20240620" 
        self.app = app
        
        # Initialize rate limiter
        self.limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=["100 per day", "10 per hour"]
        )

    async def invoke_model(self, system_message: str, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        try:
            logger.info("Invoking Anthropic model")
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    system=system_message,
                    messages=messages
                ),
                timeout=30
            )
            logger.info("Received response from Anthropic model")
            return response.content
        except asyncio.TimeoutError:
            logger.error("Timeout occurred while invoking Anthropic model")
            raise
        except Exception as e:
            logger.error(f"Error invoking Anthropic model: {str(e)}", exc_info=True)
            raise

    def _sanitize_input(self, input_data: str) -> str:
        sanitized = re.sub(r'\b(UNION|SELECT|FROM|WHERE|INSERT|DELETE|UPDATE|DROP)\b', '', input_data, flags=re.IGNORECASE)
        sanitized = re.sub(r'<[^>]*?>', '', sanitized)
        max_length = 100000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning(f"Input truncated to {max_length} characters")
        try:
            json.loads(sanitized)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON after truncation: {e}")
            last_brace = sanitized.rfind('}')
            if last_brace != -1:
                sanitized = sanitized[:last_brace+1]
            else:
                raise ValueError("Unable to create valid JSON from truncated input")
        return sanitized

    def _filter_output(self, output: Union[str, List]) -> str:
        if isinstance(output, list):
            logger.info(f"Received list output from Anthropic API: {output}")
            output = output[0].text if output and hasattr(output[0], 'text') else str(output)
        elif not isinstance(output, str):
            logger.warning(f"Unexpected output type in _filter_output: {type(output)}")
            output = str(output)

        filtered = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]', output)
        filtered = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE REDACTED]', filtered)
        filtered = re.sub(r'\b(UNION|SELECT|FROM|WHERE|INSERT|DELETE|UPDATE|DROP)\b', '[SQL REDACTED]', filtered, flags=re.IGNORECASE)
        filtered = re.sub(r'<[^>]*?>', '[HTML REDACTED]', filtered)
        return filtered

    async def match_patient_to_trials(self, patient_data: Dict[str, Any], trials_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            sanitized_patient_data = sanitize_for_json(patient_data)
            sanitized_trials_data = sanitize_for_json(trials_data)

            system_message = "You are an AI assistant tasked with matching patients to clinical trials based on their profiles and trial eligibility criteria."
            
            prompt = self._construct_matching_prompt(sanitized_patient_data, sanitized_trials_data)
            
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            logger.info("Sending request to Anthropic API")
            response = await self.invoke_model(system_message, messages)
            logger.info(f"Received response from Anthropic API: {response[:100]}...")  # Log first 100 chars
            filtered_response = self._filter_output(response)
            
            parsed_response = self._parse_matching_response(filtered_response)
            logger.info(f"Parsed {len(parsed_response)} matches from Anthropic response")
            return parsed_response
        except Exception as e:
            logger.error(f"Unexpected error in match_patient_to_trials: {str(e)}", exc_info=True)
            return []  # Return an empty list instead of raising an exception

    def _construct_matching_prompt(self, patient_data, trials_data):
        # Implement token counting here to ensure we don't exceed limits
        max_tokens = 10000  # Adjust based on your plan's limits
        patient_json = json_serialize(patient_data)
        trials_json = json_serialize(trials_data)
        
        while len(patient_json) + len(trials_json) > max_tokens:
            if len(trials_data) > 1:
                trials_data = trials_data[:-1]  # Remove the last trial
                trials_json = json_serialize(trials_data)
            else:
                raise ValueError("Cannot construct prompt within token limit")

        prompt = f"""
        Patient Profile:
        {patient_json}

        Clinical Trials:
        {trials_json}

        Based on the patient profile and clinical trial data provided, please match the patient to suitable trials.
        For each suitable trial, provide a compatibility score between 0 and 100, where 100 is a perfect match.
        Only include trials with a compatibility score of 70 or higher.
        
        Please provide the output in the following JSON format:
        [
            {{
                "nct_id": "string",
                "compatibility_score": number,
                "reasons": ["string"]
            }}
        ]

        If no trials match with a score of 70 or higher, return an empty array: []
        """
        return prompt
    
    def _parse_matching_response(self, response: str) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Parsing response: {response}")
            
            # Attempt to find JSON content within the response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start != -1 and json_end != -1:
                json_content = response[json_start:json_end]
                logger.debug(f"Extracted JSON content: {json_content}")
            else:
                logger.warning("Could not find JSON content in the response")
                return []

            matches = json.loads(json_content)
            
            if not isinstance(matches, list):
                logger.warning(f"Expected a list of matches, but got: {type(matches)}")
                if isinstance(matches, dict):
                    matches = [matches]  # Convert single dict to list
                    logger.info("Converted single dict to list")
                else:
                    logger.error(f"Unexpected response format: {matches}")
                    return []
            
            validated_matches = []
            for match in matches:
                if not all(key in match for key in ('nct_id', 'compatibility_score', 'reasons')):
                    logger.warning(f"Skipping invalid match: {match}")
                    continue
                if not isinstance(match['compatibility_score'], (int, float)) or not (0 <= match['compatibility_score'] <= 100):
                    logger.warning(f"Invalid compatibility score in match: {match}")
                    continue
                if not isinstance(match['reasons'], list):
                    logger.warning(f"Invalid reasons format in match: {match}")
                    continue
                validated_matches.append(match)
            
            logger.info(f"Validated {len(validated_matches)} out of {len(matches)} matches")
            return validated_matches
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing matching response: {str(e)}")
            logger.error(f"Response content: {response}")
            return []
        except Exception as e:
            logger.error(f"Error in _parse_matching_response: {str(e)}")
            return []

    async def analyze_eligibility_criteria(self, criteria: str) -> Dict[str, Any]:
        try:
            sanitized_criteria = self._sanitize_input(criteria)
            prompt = f"""
            Analyze the following eligibility criteria and extract key information:

            {sanitized_criteria}

            Provide a structured analysis including:
            1. Inclusion criteria
            2. Exclusion criteria
            3. Age range
            4. Required medical conditions
            5. Prohibited medical conditions or treatments

            Return the analysis as a JSON object.
            """

            messages = [
                {"role": "system", "content": "You are an AI assistant tasked with analyzing clinical trial eligibility criteria."},
                {"role": "user", "content": prompt}
            ]

            response = await self.invoke_model(messages)
            filtered_response = self._filter_output(response)

            try:
                return json.loads(filtered_response)
            except json.JSONDecodeError:
                logger.error(f"Error parsing eligibility criteria analysis: Invalid JSON")
                return {}
        except Exception as e:
            logger.error(f"Error in analyze_eligibility_criteria: {str(e)}", exc_info=True)
            return {}