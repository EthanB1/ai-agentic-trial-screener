# app/models/patient.py

from bson import ObjectId
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.database import get_db
from app.utils.logging_config import get_logger
from app.utils.error_handlers import handle_database_error
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

logger = get_logger(__name__)

class Patient:
    def __init__(self, **kwargs: Any):
        self.id: Optional[ObjectId] = kwargs.get('_id')
        if self.id and not isinstance(self.id, ObjectId):
            self.id = ObjectId(self.id)
        self.user_id: str = kwargs.get('user_id', '')
        self.email: str = kwargs.get('email', '')
        self.first_name: str = kwargs.get('first_name', '')
        self.last_name: str = kwargs.get('last_name', '')
        self.date_of_birth: Optional[datetime] = kwargs.get('date_of_birth')
        self.gender: str = kwargs.get('gender', '')
        self.medical_conditions: List[str] = kwargs.get('medical_conditions', [])
        self.medications: List[str] = kwargs.get('medications', [])
        self.ethnicity: str = kwargs.get('ethnicity', '')
        self.family_medical_history: str = kwargs.get('family_medical_history', '')
        self.consent_to_contact: bool = kwargs.get('consentToContact', False)
        
        # Store any additional fields
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    @staticmethod
    async def create_patient(patient_data: Dict[str, Any]) -> Optional[str]:
        try:
            db = await get_db()
            result = await db.patients.insert_one(patient_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating patient: {str(e)}")
            return None

    @staticmethod
    async def get_patient_by_user_id(user_id: str) -> Optional['Patient']:
        try:
            db = await get_db()
            patient_data = await db.patients.find_one({'user_id': user_id})
            if patient_data:
                return Patient(**patient_data)
            return None
        except Exception as e:
            logger.error(f"Error fetching patient with user_id {user_id}: {str(e)}")
            return None

    def to_dict(self) -> Dict[str, Any]:
        logger.info(f"Date of birth type: {type(self.date_of_birth)}")
        return {
            'user_id': self.user_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth if isinstance(self.date_of_birth, str) else self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'medical_conditions': self.medical_conditions,
            'medications': self.medications,
            'ethnicity': self.ethnicity,
            'family_medical_history': self.family_medical_history,
            'consent_to_contact': self.consent_to_contact
        }
    
    @staticmethod
    async def create_patient(patient_data: Dict[str, Any]) -> Optional[str]:
        try:
            db = await get_db()
            result = await db.patients.insert_one(patient_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating patient: {str(e)}")
            return None

    async def update(self) -> bool:
        try:
            db = await get_db()
            result = await db.patients.update_one(
                {'_id': self.id},
                {'$set': self.to_dict()}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating patient {self.id}: {str(e)}")
            return False
