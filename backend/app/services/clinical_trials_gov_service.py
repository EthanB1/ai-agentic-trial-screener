# app/services/clinical_trials_gov_service.py

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import aiohttp
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.input_sanitizer import sanitize_trial_data, sanitize_mongo_query
from app.database import get_db

logger = logging.getLogger(__name__)

class ClinicalTrialsGovService:
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    MAX_RETRIES = 5
    BACKOFF_FACTOR = 0.5
    RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]

    @staticmethod
    async def fetch_trials(page_token: Optional[str] = None, limit: int = 100, min_date: Optional[datetime] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        params = {
            "format": "json",
            "fields": "NCTId,BriefTitle,OfficialTitle,BriefSummary,DetailedDescription,OverallStatus,Phase,Condition,EligibilityCriteria,LastUpdatePostDate",
            "pageSize": limit
        }
        if page_token:
            params["pageToken"] = page_token
        if min_date:
            params["query.lastUpdatePostDate"] = f"RANGE[{min_date.strftime('%Y-%m-%d')},MAX]"

        async with aiohttp.ClientSession() as session:
            for attempt in range(ClinicalTrialsGovService.MAX_RETRIES):
                try:
                    async with session.get(ClinicalTrialsGovService.BASE_URL, params=params, timeout=30) as response:
                        response.raise_for_status()
                        data = await response.json()
                        return data.get('studies', []), data.get('nextPageToken')
                except aiohttp.ClientResponseError as e:
                    logger.error(f"HTTP error while fetching trials: {e.status}: {e.message}")
                    if e.status not in ClinicalTrialsGovService.RETRY_STATUS_FORCELIST or attempt == ClinicalTrialsGovService.MAX_RETRIES - 1:
                        raise
                except aiohttp.ClientError as e:
                    logger.error(f"Network error while fetching trials: {str(e)}")
                    raise
                except asyncio.TimeoutError:
                    logger.error("Request timed out while fetching trials")
                    if attempt == ClinicalTrialsGovService.MAX_RETRIES - 1:
                        raise
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON response: {str(e)}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error while fetching trials: {str(e)}")
                    raise
                
                await asyncio.sleep(ClinicalTrialsGovService.BACKOFF_FACTOR * (2 ** attempt))

    @staticmethod
    def process_trials(trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed_trials = []
        for trial in trials:
            try:
                processed_trial = {
                    'nct_id': trial.get('protocolSection', {}).get('identificationModule', {}).get('nctId', ''),
                    'brief_title': trial.get('protocolSection', {}).get('identificationModule', {}).get('briefTitle', ''),
                    'official_title': trial.get('protocolSection', {}).get('identificationModule', {}).get('officialTitle', ''),
                    'brief_summary': trial.get('protocolSection', {}).get('descriptionModule', {}).get('briefSummary', ''),
                    'detailed_description': trial.get('protocolSection', {}).get('descriptionModule', {}).get('detailedDescription', ''),
                    'status': trial.get('protocolSection', {}).get('statusModule', {}).get('overallStatus', ''),
                    'phase': trial.get('protocolSection', {}).get('designModule', {}).get('phases', []),
                    'conditions': trial.get('protocolSection', {}).get('conditionsModule', {}).get('conditions', []),
                    'eligibility': trial.get('protocolSection', {}).get('eligibilityModule', {}).get('eligibilityCriteria', ''),
                    'last_update_posted': trial.get('protocolSection', {}).get('statusModule', {}).get('lastUpdatePostDate', '')
                }
                processed_trials.append(sanitize_trial_data(processed_trial))
            except KeyError as e:
                logger.warning(f"Skipping trial due to missing data: {str(e)}")
        return processed_trials

    @staticmethod
    async def save_trials(trials: List[Dict[str, Any]]) -> Tuple[int, int]:
        db: AsyncIOMotorDatabase = await get_db()
        saved_count = 0
        updated_count = 0
        for trial in trials:
            try:
                result = await db.clinical_trials.update_one(
                    sanitize_mongo_query({'nct_id': trial['nct_id']}),
                    {'$set': trial},
                    upsert=True
                )
                if result.upserted_id:
                    saved_count += 1
                    logger.info(f"Added new trial: {trial['nct_id']}")
                elif result.modified_count > 0:
                    updated_count += 1
                    logger.info(f"Updated existing trial: {trial['nct_id']}")
            except Exception as e:
                logger.error(f"Error saving trial {trial.get('nct_id', 'Unknown')}: {str(e)}")
        return saved_count, updated_count

    @staticmethod
    async def get_most_recent_trial_date() -> Optional[datetime]:
        db: AsyncIOMotorDatabase = await get_db()
        most_recent_trial = await db.clinical_trials.find_one(
            sanitize_mongo_query({"last_update_posted": {"$ne": None, "$ne": ""}}),
            sort=[('last_update_posted', -1)]
        )
        if most_recent_trial and most_recent_trial.get('last_update_posted'):
            try:
                return datetime.strptime(most_recent_trial['last_update_posted'], '%Y-%m-%d')
            except ValueError:
                logger.error(f"Invalid date format for last_update_posted: {most_recent_trial['last_update_posted']}")
        logger.info("No existing trials found in the database. Fetching all available trials.")
        return None

    @staticmethod
    async def fetch_and_save_trials(num_trials: int = 300, batch_size: int = 100) -> Tuple[int, int]:
        total_saved = 0
        total_updated = 0
        next_page_token = None
        min_date = await ClinicalTrialsGovService.get_most_recent_trial_date()
        
        logger.info(f"Starting fetch of trials updated after {min_date}")
        
        while total_saved + total_updated < num_trials or num_trials == 0:
            try:
                fetched_trials, next_page_token = await ClinicalTrialsGovService.fetch_trials(
                    page_token=next_page_token,
                    limit=batch_size,
                    min_date=min_date
                )
                logger.info(f"Fetched {len(fetched_trials)} trials")
                if not fetched_trials:
                    logger.info("No trials fetched. Ending fetch process.")
                    break
                
                processed_trials = ClinicalTrialsGovService.process_trials(fetched_trials)
                saved_in_batch, updated_in_batch = await ClinicalTrialsGovService.save_trials(processed_trials)
                total_saved += saved_in_batch
                total_updated += updated_in_batch
                logger.info(f"Batch complete. New: {saved_in_batch}, Updated: {updated_in_batch}. Total new: {total_saved}, Total updated: {total_updated}")
                
                if not next_page_token:
                    logger.info("No more pages to fetch.")
                    break
                
                if num_trials > 0 and total_saved + total_updated >= num_trials:
                    logger.info(f"Reached desired number of trials ({num_trials}).")
                    break
                
                await asyncio.sleep(2)  # Delay between requests to avoid rate limiting
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                break  # Exit the loop on error instead of raising an exception
        
        logger.info(f"Fetch complete. Total new trials: {total_saved}, Total updated trials: {total_updated}")
        return total_saved, total_updated

    @staticmethod
    async def get_database_statistics() -> Dict[str, Any]:
        db: AsyncIOMotorDatabase = await get_db()
        try:
            total_trials = await db.clinical_trials.count_documents({})
            
            earliest_trial = await db.clinical_trials.find_one(
                sanitize_mongo_query({"last_update_posted": {"$ne": None, "$ne": ""}}),
                sort=[('last_update_posted', 1)]
            )
            latest_trial = await db.clinical_trials.find_one(
                sanitize_mongo_query({"last_update_posted": {"$ne": None, "$ne": ""}}),
                sort=[('last_update_posted', -1)]
            )

            earliest_date = datetime.strptime(earliest_trial['last_update_posted'], '%Y-%m-%d') if earliest_trial and earliest_trial.get('last_update_posted') else None
            latest_date = datetime.strptime(latest_trial['last_update_posted'], '%Y-%m-%d') if latest_trial and latest_trial.get('last_update_posted') else None

            status_counts = await ClinicalTrialsGovService._aggregate_count(db.clinical_trials, "status")
            phase_counts = await ClinicalTrialsGovService._aggregate_count(db.clinical_trials, "phase", unwind=True)

            return {
                "total_trials": total_trials,
                "date_range": {
                    "earliest": earliest_date.strftime('%Y-%m-%d') if earliest_date else None,
                    "latest": latest_date.strftime('%Y-%m-%d') if latest_date else None
                },
                "status_counts": status_counts or {},
                "phase_counts": phase_counts or {}
            }
        except Exception as e:
            logger.error(f"Error in get_database_statistics: {str(e)}")
            return {
                "total_trials": 0,
                "date_range": {"earliest": None, "latest": None},
                "status_counts": {},
                "phase_counts": {}
            }

    @staticmethod
    async def _aggregate_count(collection, field: str, unwind: bool = False) -> Dict[str, int]:
        try:
            pipeline = []
            if unwind:
                pipeline.append({"$unwind": f"${field}"})
            pipeline.extend([
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$project": {"_id": 0, "value": "$_id", "count": 1}}
            ])
            
            cursor = collection.aggregate(pipeline)
            result = await cursor.to_list(length=None)
            return {item['value']: item['count'] for item in result if item['value'] is not None}
        except Exception as e:
            logger.error(f"Error in _aggregate_count for field {field}: {str(e)}")
            return {}