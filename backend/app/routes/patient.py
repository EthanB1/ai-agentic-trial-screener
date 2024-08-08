# app/routes/patient.py

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.patient import Patient
from app.utils.input_sanitizer import sanitize_input
from app.utils.error_handlers import handle_database_error, handle_not_found_error

patient = Blueprint('patient', __name__)
logger = logging.getLogger(__name__)

@patient.route('/profile', methods=['GET'])
@jwt_required()
async def get_patient_profile():
    current_user = get_jwt_identity()
    logger.info(f"Fetching profile for user: {current_user}")
    try:
        patient = await Patient.get_patient_by_user_id(current_user)
        if patient:
            logger.info(f"Profile found for user: {current_user}")
            return jsonify({
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'date_of_birth': patient.date_of_birth,
                'gender': patient.gender,
                'medical_conditions': patient.medical_conditions or [],
                'medications': patient.medications or []
            }), 200
        else:
            logger.warning(f"No profile found for user: {current_user}")
            return jsonify({"error": "Patient profile not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching profile for user {current_user}: {str(e)}")
        return jsonify({"error": "An error occurred while fetching the profile"}), 500
    
@patient.route('/profile', methods=['PUT'])
@jwt_required()
async def update_patient_profile():
    current_user = get_jwt_identity()
    data = request.get_json()
    logger.info(f"Updating profile for user: {current_user}")
    try:
        sanitized_data = {k: sanitize_input(v) for k, v in data.items()}
        
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'medical_conditions', 'medications']
        for field in required_fields:
            if field not in sanitized_data:
                return jsonify({'message': f'Missing required field: {field}'}), 400

        success = await Patient.update_patient(current_user, sanitized_data)
        if success:
            return jsonify({'message': 'Patient profile updated successfully'}), 200
        else:
            return handle_not_found_error("Failed to update patient profile")
    except Exception as e:
        return handle_database_error(str(e))