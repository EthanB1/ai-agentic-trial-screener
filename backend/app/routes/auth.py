# app/routes/auth.py

from flask import Blueprint, request, jsonify
from app.models.user import User
from app.models.patient import Patient
from flask_jwt_extended import create_access_token
from app.utils.input_sanitizer import sanitize_input
from app.utils.error_handlers import handle_database_error, handle_invalid_input_error
import logging
from flask_jwt_extended import create_access_token, create_refresh_token

auth = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth.route('/register', methods=['POST'])
async def register():
    try:
        data = request.get_json()
        if not data:
            return handle_invalid_input_error('No data provided')

        email = sanitize_input(data.get('email'))
        password = data.get('password')  # Don't sanitize passwords
        first_name = sanitize_input(data.get('firstName'))
        last_name = sanitize_input(data.get('lastName'))

        if not email or not password or not first_name or not last_name:
            return handle_invalid_input_error('Email, password, first name, and last name are required')

        existing_user = await User.get_user_by_email(email)
        if existing_user:
            return handle_invalid_input_error('User already exists')

        user_id = await User.create_user(email, password)
        
        # Create a patient profile
        patient_data = {
            'user_id': user_id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': '',
            'gender': '',
            'medical_conditions': [],
            'medications': [],
            'ethnicity': '',
            'family_medical_history': ''
        }
        patient_id = await Patient.create_patient(patient_data)

        if not patient_id:
            logger.error(f"Failed to create patient profile for user {user_id}")
            return jsonify({'error': 'Failed to create patient profile'}), 500

        logger.info(f"User created successfully with ID: {user_id}")
        return jsonify({'message': 'User created successfully', 'user_id': user_id}), 201

    except Exception as e:
        return handle_database_error(str(e))
    
@auth.route('/login', methods=['POST'])
async def login():
    try:
        data = request.get_json()
        email = sanitize_input(data.get('email'))
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Email and password are required'}), 400

        user = await User.get_user_by_email(email)
        if user and await user.check_password(password):
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': str(user.id)
            }), 200
        else:
            return jsonify({'message': 'Invalid email or password'}), 401

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'An error occurred during login'}), 500