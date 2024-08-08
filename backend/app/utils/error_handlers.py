# app/utils/error_handlers.py

import traceback
from flask import jsonify
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

def handle_database_error(e):
    error_msg = f"Database error: {str(e)}"
    stack_trace = traceback.format_exc()
    logger.error(f"{error_msg}\n{stack_trace}")
    return jsonify({
        "error": "Database Error",
        "message": error_msg,
        "stack_trace": stack_trace
    }), 500

def handle_anthropic_error(e):
    error_msg = f"Anthropic API error: {str(e)}"
    stack_trace = traceback.format_exc()
    logger.error(f"{error_msg}\n{stack_trace}")
    return jsonify({
        "error": "Anthropic API Error",
        "message": error_msg,
        "stack_trace": stack_trace
    }), 500

def handle_general_error(e):
    error_msg = f"General error: {str(e)}"
    stack_trace = traceback.format_exc()
    logger.error(f"{error_msg}\n{stack_trace}")
    return jsonify({
        "error": "General Error",
        "message": error_msg,
        "stack_trace": stack_trace
    }), 500

def handle_not_found_error(error_message):
    logger.warning(f"Not found error: {error_message}")
    return jsonify({
        "error": "Not Found",
        "message": error_message
    }), 404

def handle_invalid_input_error(error_message):
    logger.warning(f"Invalid input: {error_message}")
    return jsonify({
        "error": "Invalid Input",
        "message": error_message
    }), 400