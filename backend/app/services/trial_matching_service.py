# app/services/trial_matching_service.py

import asyncio
import logging
from typing import Dict, Any, List, Union
from datetime import datetime
from bson import ObjectId
from tenacity import retry, stop_after_attempt, wait_exponential
from app.models.patient import Patient
from app.services.anthropic_service import AnthropicService
from app.services.clinical_trials_gov_service import ClinicalTrialsGovService
from app.database import get_db
from app.utils.error_handlers import handle_general_error, handle_anthropic_error
from app.utils.input_sanitizer import sanitize_patient_data, sanitize_trial_data

logger = logging.getLogger(__name__)

class TrialMatchingService:
    def __init__(self, anthropic_service, clinical_trials_service):
        self.anthropic_service = anthropic_service
        self.clinical_trials_service = clinical_trials_service
        self.stop_matching = {}

    async def match_patient_to_trials(self, user_id: Union[str, ObjectId]) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Starting trial matching for user: {user_id}")
            db = await get_db()
            patient = await Patient.get_patient_by_user_id(user_id)
            
            if not patient:
                logger.warning(f"No patient profile found for user {user_id}")
                return []

            all_matches = []
            batch_size = 50
            skip = 0
            total_trials = await db.clinical_trials.count_documents({})

            logger.info(f"Total trials to process: {total_trials}")

            while skip < total_trials and not self.stop_matching.get(str(user_id), False):
                try:
                    trials_cursor = db.clinical_trials.find().skip(skip).limit(batch_size)
                    trials = await trials_cursor.to_list(length=batch_size)
                    
                    if not trials:
                        logger.info(f"No more trials to process for user {user_id}")
                        break

                    logger.info(f"Processing batch of {len(trials)} trials for user {user_id}")
                    
                    matches = await self.call_anthropic_with_retry(patient.__dict__, trials)
                    valid_matches = [match for match in matches if match.get('compatibility_score', 0) >= 70]
                    
                    if valid_matches:
                        new_matches = await self.filter_and_save_new_matches(user_id, valid_matches)
                        all_matches.extend(new_matches)
                        # Assuming emit_trial_matches is defined elsewhere
                        await self.emit_trial_matches(str(user_id), new_matches)

                    logger.info(f"Processed batch. Total matches so far: {len(all_matches)}")

                except Exception as e:
                    logger.error(f"Error processing batch for user {user_id}: {str(e)}", exc_info=True)

                skip += batch_size
                logger.info(f"Moving to next batch. Skip: {skip}, Total trials: {total_trials}")
                await asyncio.sleep(1)  # Add a 1-second delay between batches

            if not all_matches:
                logger.info(f"No new matching trials found for user: {user_id}")
            else:
                logger.info(f"Matching process completed for user {user_id}. Total new matches: {len(all_matches)}")

            return all_matches

        except asyncio.CancelledError:
            logger.info(f"Matching task cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Error in match_patient_to_trials for user {user_id}: {str(e)}", exc_info=True)
        finally:
            self.stop_matching.pop(str(user_id), None)

        return all_matches

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_anthropic_with_retry(self, patient_data, trials_data):
        try:
            return await asyncio.wait_for(
                self.anthropic_service.match_patient_to_trials(patient_data, trials_data),
                timeout=60  # 60 seconds timeout
            )
        except asyncio.TimeoutError:
            logger.error("Anthropic API call timed out")
            raise
        except Exception as e:
            logger.error(f"Error in Anthropic API call: {str(e)}", exc_info=True)
            raise

    async def filter_and_save_new_matches(self, user_id: Union[str, ObjectId], matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        db = await get_db()
        new_matches = []
        for match in matches:
            existing_match = await db.trial_matches.find_one({
                'user_id': str(user_id),
                'nct_id': match['nct_id']
            })
            if not existing_match:
                match['user_id'] = str(user_id)
                match['timestamp'] = datetime.utcnow()
                await db.trial_matches.insert_one(match)
                new_matches.append(match)
            else:
                logger.info(f"Trial {match['nct_id']} already matched for user {user_id}")
        return new_matches

    async def start_matching_process(self, user_id: str):
        if user_id in self.stop_matching:
            logger.warning(f"Matching process already running for user {user_id}")
            return {"message": "Matching process already running"}

        self.stop_matching[user_id] = False
        try:
            matches = await self.match_patient_to_trials(user_id)
            return {"message": "Matching process completed", "matches": len(matches)}
        except Exception as e:
            logger.error(f"Error in matching process for user {user_id}: {str(e)}", exc_info=True)
            return {"message": f"Error in matching process: {str(e)}"}

    async def stop_matching_process(self, user_id: str):
        if user_id in self.stop_matching:
            self.stop_matching[user_id] = True
            logger.info(f"Stop signal sent for user {user_id}")
            return {"message": "Stop signal sent to matching process"}
        else:
            return {"message": "No active matching process found for this user"}

    async def get_matching_status(self, user_id: str):
        if user_id in self.stop_matching:
            return {"status": "in_progress" if not self.stop_matching[user_id] else "stopping"}
        else:
            return {"status": "not_running"}