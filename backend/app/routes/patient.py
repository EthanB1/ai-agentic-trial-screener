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
            return jsonify(patient.to_dict()), 200
        else:
            logger.warning(f"No profile found for user: {current_user}")
            return jsonify({"error": "Patient profile not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching profile for user {current_user}: {str(e)}")
        return handle_database_error(e)

@patient.route('/profile', methods=['PUT'])
@jwt_required()
async def update_patient_profile():
    current_user = get_jwt_identity()
    data = request.get_json()
    logger.info(f"Updating profile for user: {current_user}")
    try:
        patient = await Patient.get_patient_by_user_id(current_user)
        if not patient:
            return jsonify({'error': 'Patient profile not found'}), 404

        # Update patient fields
        for key, value in data.items():
            if hasattr(patient, key):
                setattr(patient, key, value)

        success = await patient.update()
        if success:
            return jsonify({'message': 'Patient profile updated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to update patient profile'}), 500
    except Exception as e:
        logger.error(f"Error updating profile for user {current_user}: {str(e)}")
        return handle_database_error(e)

