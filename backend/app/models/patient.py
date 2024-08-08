# app/models/patient.py

from app.database import get_db
from bson import ObjectId
import logging
import pymongo
from app.models import user

logger = logging.getLogger(__name__)

class Patient:
    def __init__(self, user_id, first_name, last_name, date_of_birth, gender, medical_conditions, medications):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.gender = gender
        self.medical_conditions = medical_conditions if isinstance(medical_conditions, list) else []
        self.medications = medications if isinstance(medications, list) else []

    @staticmethod
    async def create_patient(user_id, first_name, last_name, date_of_birth, gender, medical_conditions=None, medications=None):
        db = await get_db()
        try:
            # Ensure email is not null
            email = await user.User.get_email_by_user_id(user_id)
            if not email:
                raise ValueError("Cannot create patient profile without an email address")

            result = await db.patients.insert_one({
                'user_id': user_id,
                'email': email,  # Add email to the patient document
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': date_of_birth,
                'gender': gender,
                'medical_conditions': medical_conditions if isinstance(medical_conditions, list) else [],
                'medications': medications if isinstance(medications, list) else []
            })
            logger.info(f"Created patient profile for user: {user_id}")
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            logger.error(f"Patient profile already exists for user: {user_id}")
            raise ValueError("Patient profile already exists")
        except Exception as e:
            logger.error(f"Error creating patient profile: {str(e)}")
            raise

    @staticmethod
    async def get_patient_by_user_id(user_id):
        db = await get_db()
        try:
            patient_data = await db.patients.find_one({'user_id': user_id})
            if patient_data:
                return Patient(
                    patient_data['user_id'],
                    patient_data['first_name'],
                    patient_data['last_name'],
                    patient_data['date_of_birth'],
                    patient_data['gender'],
                    patient_data.get('medical_conditions', []),
                    patient_data.get('medications', [])
                )
            logger.warning(f"No patient profile found for user: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching patient profile: {str(e)}")
            raise

    @staticmethod
    async def update_patient(user_id, data):
        db = await get_db()
        try:
            # Ensure medical_conditions and medications are always arrays
            if 'medical_conditions' in data and data['medical_conditions'] is None:
                data['medical_conditions'] = []
            if 'medications' in data and data['medications'] is None:
                data['medications'] = []

            result = await db.patients.update_one(
                {'user_id': user_id},
                {'$set': data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated patient profile for user: {user_id}")
                return True
            else:
                logger.warning(f"No patient profile found to update for user: {user_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating patient profile: {str(e)}")
            raise