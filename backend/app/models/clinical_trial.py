# app/models/clinical_trial.py

from flask import current_app
from bson import ObjectId
import logging

class ClinicalTrial:
    def __init__(self, nct_id, brief_title, official_title, brief_summary, detailed_description, status, phase, conditions, eligibility):
        self.nct_id = nct_id
        self.brief_title = brief_title
        self.official_title = official_title
        self.brief_summary = brief_summary
        self.detailed_description = detailed_description
        self.status = status
        self.phase = phase
        self.conditions = conditions
        self.eligibility = eligibility

    @staticmethod
    def create_trial(nct_id, brief_title, official_title, brief_summary, detailed_description, status, phase, conditions, eligibility):
        db = current_app.db
        try:
            result = db.clinical_trials.insert_one({
                'nct_id': nct_id,
                'brief_title': brief_title,
                'official_title': official_title,
                'brief_summary': brief_summary,
                'detailed_description': detailed_description,
                'status': status,
                'phase': phase,
                'conditions': conditions,
                'eligibility': eligibility
            })
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f"Error creating trial {nct_id}: {str(e)}")
            return None

    @staticmethod
    def get_trial_by_nct_id(nct_id):
        db = current_app.db
        trial_data = db.clinical_trials.find_one({'nct_id': nct_id})
        if trial_data:
            return ClinicalTrial(
                trial_data['nct_id'],
                trial_data['brief_title'],
                trial_data['official_title'],
                trial_data['brief_summary'],
                trial_data['detailed_description'],
                trial_data['status'],
                trial_data['phase'],
                trial_data['conditions'],
                trial_data['eligibility']
            )
        return None

    @staticmethod
    def get_all_trials():
        db = current_app.db
        trials = db.clinical_trials.find()
        return [ClinicalTrial(**trial) for trial in trials]