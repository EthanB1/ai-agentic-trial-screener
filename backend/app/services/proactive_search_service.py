# app/services/proactive_search_service.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from bson import ObjectId

from app.services.trial_matching_service import TrialMatchingService
from app.services.clinical_trials_gov_service import ClinicalTrialsGovService
from app.services.email_service import EmailService
from app.database import get_db
from app.utils.input_sanitizer import sanitize_patient_data, sanitize_trial_data, sanitize_mongo_query

logger = logging.getLogger(__name__)

class ProactiveSearchService:
    def __init__(self, trial_matching_service: TrialMatchingService, clinical_trials_service: ClinicalTrialsGovService):
        self.trial_matching_service = trial_matching_service
        self.clinical_trials_service = clinical_trials_service
        self.email_service = EmailService.get_instance()

    async def run_proactive_search(self):
        """
        Main method to run the proactive search process.
        Fetches new trials, processes them, and matches them with patients.
        """
        try:
            logger.info("Starting proactive search for new trials")
            
            # Fetch new trials
            new_trials = await self.fetch_new_trials()
            if not new_trials:
                logger.info("No new trials found.")
                return

            # Process and save new trials
            processed_trials = await self.process_and_save_trials(new_trials)

            # Match new trials with existing patients
            await self.match_trials_with_patients(processed_trials)

            # Update last check date
            await self.update_last_check_date()

            logger.info("Proactive search completed successfully")
        except Exception as e:
            logger.error(f"Error in proactive search: {str(e)}")
            # Consider implementing a notification system for critical errors

    async def fetch_new_trials(self) -> List[Dict[str, Any]]:
        """
        Fetch new trials from ClinicalTrials.gov since the last check.
        
        Returns:
            List[Dict[str, Any]]: A list of new trial data
        
        Raises:
            RuntimeError: If there's an error fetching trials
        """
        try:
            last_check = await self.get_last_check_date()
            logger.info(f"Fetching trials updated since {last_check}")
            return await self.clinical_trials_service.fetch_trials(min_date=last_check)
        except Exception as e:
            logger.error(f"Error fetching new trials: {str(e)}")
            raise RuntimeError("Failed to fetch new trials") from e

    async def process_and_save_trials(self, trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and save new trials to the database.
        
        Args:
            trials (List[Dict[str, Any]]): List of new trials to process
        
        Returns:
            List[Dict[str, Any]]: List of processed trials
        """
        processed_trials = []
        db = await get_db()
        for trial in trials:
            try:
                safe_trial = sanitize_trial_data(trial)
                analyzed_criteria = await self.trial_matching_service.anthropic_service.analyze_eligibility_criteria(safe_trial['eligibility_criteria'])
                safe_trial['analyzed_criteria'] = analyzed_criteria

                result = await db.clinical_trials.update_one(
                    sanitize_mongo_query({'nct_id': safe_trial['nct_id']}),
                    {'$set': safe_trial},
                    upsert=True
                )
                if result.upserted_id or result.modified_count > 0:
                    processed_trials.append(safe_trial)
                    logger.info(f"Processed and saved trial: {safe_trial['nct_id']}")
            except Exception as e:
                logger.error(f"Error processing trial {trial.get('nct_id', 'Unknown')}: {str(e)}")

        return processed_trials

    async def match_trials_with_patients(self, trials: List[Dict[str, Any]]):
        """
        Match new trials with existing patients.

        Args:
            trials (List[Dict[str, Any]]): List of new trials to match
        """
        try:
            db = await get_db()
            patients_cursor = db.patients.find()

            async for patient in patients_cursor:
                try:
                    safe_patient = sanitize_patient_data(patient)
                    matching_trials = await self.trial_matching_service.match_patient_to_trials(str(safe_patient['_id']))
                    if matching_trials:
                        await self.notify_patient(safe_patient, matching_trials)
                        await self.update_patient_matches(safe_patient['_id'], matching_trials)
                except Exception as e:
                    logger.error(f"Error matching trials for patient {patient.get('_id', 'Unknown')}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in match_trials_with_patients: {str(e)}")
            raise RuntimeError("Failed to match trials with patients") from e
        
    async def notify_patient(self, patient: Dict[str, Any], matching_trials: List[Dict[str, Any]]):
        """
        Notify a patient about new matching trials.
        
        Args:
            patient (Dict[str, Any]): Patient data
            matching_trials (List[Dict[str, Any]]): List of matching trials
        """
        try:
            logger.info(f"Notifying patient {patient['_id']} of {len(matching_trials)} new matching trials")

            if 'email' not in patient or not patient['email']:
                logger.warning(f"No email address found for patient {patient['_id']}")
                return

            email_sent = await self.email_service.send_trial_match_email(
                patient['email'],
                f"{patient['first_name']} {patient['last_name']}",
                matching_trials
            )

            if email_sent:
                logger.info(f"Email notification sent to patient {patient['_id']}")
                await self.update_patient_notification(patient['_id'])
            else:
                logger.error(f"Failed to send email notification to patient {patient['_id']}")
        except Exception as e:
            logger.error(f"Error notifying patient {patient['_id']}: {str(e)}")
            raise RuntimeError(f"Failed to notify patient {patient['_id']}") from e

    async def update_patient_matches(self, patient_id: ObjectId, new_matches: List[Dict[str, Any]]):
        """
        Update a patient's trial matches in the database.
        
        Args:
            patient_id (ObjectId): Patient's ID
            new_matches (List[Dict[str, Any]]): List of new matching trials
        """
        try:
            db = await get_db()
            result = await db.patients.update_one(
                sanitize_mongo_query({'_id': patient_id}),
                {'$push': {'trial_matches': {'$each': new_matches}}}
            )
            if result.modified_count == 0:
                logger.warning(f"No patient found with id {patient_id}")
        except Exception as e:
            logger.error(f"Error updating matches for patient {patient_id}: {str(e)}")
            raise RuntimeError(f"Failed to update matches for patient {patient_id}") from e
        
    async def update_patient_notification(self, patient_id: ObjectId):
        """
        Update the last notification date for a patient.
        
        Args:
            patient_id (ObjectId): Patient's ID
        """
        try:
            db = await get_db()
            result = await db.patients.update_one(
                sanitize_mongo_query({'_id': patient_id}),
                {'$set': {'last_notified': datetime.utcnow()}}
            )
            if result.modified_count == 0:
                logger.warning(f"No patient found with id {patient_id}")
        except Exception as e:
            logger.error(f"Error updating notification date for patient {patient_id}: {str(e)}")
            raise RuntimeError(f"Failed to update notification date for patient {patient_id}") from e

    async def get_last_check_date(self) -> datetime:
        """
        Get the date of the last proactive search check.
        
        Returns:
            datetime: Date of the last check
        """
        try:
            db = await get_db()
            last_check = await db.proactive_search_log.find_one(sort=[('check_date', -1)])
            if last_check:
                return last_check['check_date']
            return datetime.utcnow() - timedelta(days=1)  # Default to 1 day ago if no previous check
        except Exception as e:
            logger.error(f"Error getting last check date: {str(e)}")
            raise RuntimeError("Failed to retrieve last check date") from e

    async def update_last_check_date(self):
        """Update the date of the last proactive search check."""
        try:
            db = await get_db()
            await db.proactive_search_log.insert_one({'check_date': datetime.utcnow()})
        except Exception as e:
            logger.error(f"Error updating last check date: {str(e)}")
            raise RuntimeError("Failed to update last check date") from e