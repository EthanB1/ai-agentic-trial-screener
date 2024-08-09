# app/utils/input_sanitizer.py

import re
import html
import logging
from typing import Any, Dict, List, Union
from bson import ObjectId

logger = logging.getLogger(__name__)

def sanitize_input(input_data: Any) -> Any:
    """
    Sanitize input data to prevent injection attacks and ensure data integrity.

    This function handles various data types:
    - Strings: Escapes HTML entities and removes potentially dangerous characters
    - Numbers: Ensures they are within a safe range
    - Lists and Dictionaries: Recursively sanitizes their contents
    - ObjectId: Passes through unchanged
    - Other types: Converts to string and sanitizes

    Args:
        input_data: The data to be sanitized. Can be of any type.

    Returns:
        The sanitized version of the input data.

    Raises:
        ValueError: If the input data is of an unsupported type or structure.
    """
    try:
        if isinstance(input_data, str):
            # Escape HTML entities
            sanitized = html.escape(input_data)
            # Remove any potentially dangerous characters
            sanitized = re.sub(r'[^\w\s.,;:!?()-]', '', sanitized)
            # Limit the length of string inputs
            return sanitized[:1000]  # Adjust max length as needed
        
        elif isinstance(input_data, (int, float)):
            # Ensure numeric values are within acceptable ranges
            return max(min(input_data, 1e9), -1e9)  # Adjust range as needed
        
        elif isinstance(input_data, list):
            # Recursively sanitize list items
            return [sanitize_input(item) for item in input_data]
        
        elif isinstance(input_data, dict):
            # Recursively sanitize dictionary items
            return {sanitize_input(k): sanitize_input(v) for k, v in input_data.items()}
        
        elif isinstance(input_data, ObjectId):
            # Pass ObjectId through unchanged
            return input_data
        
        elif input_data is None:
            return None
        
        else:
            # For any other types, convert to string and sanitize
            logger.warning(f"Unexpected data type encountered: {type(input_data)}. Converting to string.")
            return sanitize_input(str(input_data))

    except Exception as e:
        logger.error(f"Error during input sanitization: {str(e)}")
        raise ValueError(f"Failed to sanitize input: {str(e)}") from e

def sanitize_mongo_query(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a MongoDB query to prevent NoSQL injection attacks.

    This function removes any operators that start with '$' to prevent 
    malicious query operators from being injected.

    Args:
        query (dict): The MongoDB query to sanitize.

    Returns:
        dict: The sanitized MongoDB query.

    Raises:
        ValueError: If the query is not a dictionary or contains nested operators.
    """
    if not isinstance(query, dict):
        raise ValueError("Query must be a dictionary")

    def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in d.items() if not isinstance(k, str) or not k.startswith('$')}

    try:
        sanitized_query = {}
        for key, value in query.items():
            if isinstance(value, dict):
                sanitized_query[key] = sanitize_dict(value)
            elif isinstance(value, list):
                sanitized_query[key] = [sanitize_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized_query[key] = value

        return sanitized_query
    except Exception as e:
        logger.error(f"Error during MongoDB query sanitization: {str(e)}")
        raise ValueError(f"Failed to sanitize MongoDB query: {str(e)}") from e

def sanitize_trial_data(trial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize clinical trial data specifically.

    This function applies specific sanitization rules for clinical trial data.

    Args:
        trial_data (dict): The clinical trial data to sanitize.

    Returns:
        dict: The sanitized clinical trial data.
    """
    sanitized_data = {}
    for key, value in trial_data.items():
        if key in ['nct_id', 'brief_title', 'official_title', 'phase', 'status']:
            sanitized_data[key] = sanitize_input(value)
        elif key in ['brief_summary', 'detailed_description', 'eligibility_criteria']:
            # Allow more characters for these fields, but still sanitize
            sanitized = html.escape(value)
            sanitized = re.sub(r'[^\w\s.,;:!?()/-]', '', sanitized)
            sanitized_data[key] = sanitized[:5000]  # Allow longer text for these fields
        elif key in ['conditions', 'interventions']:
            sanitized_data[key] = [sanitize_input(item) for item in value]
        elif key == 'last_update_posted':
            # Assuming this is a date string, we'll keep it as is
            sanitized_data[key] = value
        else:
            # For any unexpected fields, apply general sanitization
            sanitized_data[key] = sanitize_input(value)
    return sanitized_data

def sanitize_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize patient data specifically.

    This function applies specific sanitization rules for patient data.

    Args:
        patient_data (dict): The patient data to sanitize.

    Returns:
        dict: The sanitized patient data.
    """
    sanitized_data = {}
    for key, value in patient_data.items():
        if key in ['user_id', 'first_name', 'last_name', 'email', 'ethnicity']:
            sanitized_data[key] = sanitize_input(value)
        elif key == 'date_of_birth':
            sanitized_data[key] = value  # Assuming this is already a date object
        elif key in ['medical_conditions', 'medications']:
            sanitized_data[key] = [sanitize_input(item) for item in value]
        elif key == 'gender':
            sanitized_data[key] = value if value in ['male', 'female', 'other'] else 'other'
        elif key == 'family_medical_history':
            sanitized_data[key] = sanitize_input(value, allow_newlines=True)
        else:
            sanitized_data[key] = sanitize_input(value)
    return sanitized_data