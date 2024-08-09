# app/routes/trial_matching.py

from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.error_handlers import handle_general_error
from app.utils.input_sanitizer import sanitize_input
from app.services.trial_matching_service import TrialMatchingService
from app.database import get_db
from bson import ObjectId
import logging

# Create a Blueprint for trial matching routes
trial_matching = Blueprint('trial_matching', __name__)
logger = logging.getLogger(__name__)

@trial_matching.route('/matches', methods=['GET'])
@jwt_required()
async def get_recent_matches():
    current_user = get_jwt_identity()
    try:
        limit = 5  # Number of recent matches to return
        db = await get_db()
        
        # MongoDB aggregation pipeline to fetch and process recent matches
        pipeline = [
            {"$match": {"user_id": current_user}},
            {"$sort": {"timestamp": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "clinical_trials",
                    "localField": "nct_id",
                    "foreignField": "nct_id",
                    "as": "trial_info"
                }
            },
            {"$unwind": "$trial_info"},
            {
                "$project": {
                    "nct_id": 1,
                    "compatibility_score": 1,
                    "reasons": 1,
                    "timestamp": 1,
                    "title": "$trial_info.brief_title",
                    "brief_summary": "$trial_info.brief_summary",
                    "phase": "$trial_info.phase",
                    "status": "$trial_info.status"
                }
            }
        ]

        # Execute the aggregation pipeline
        matches = await db.trial_matches.aggregate(pipeline).to_list(length=limit)

        # Sanitize the output to prevent potential XSS or injection attacks
        sanitized_matches = [
            {
                "nct_id": sanitize_input(match['nct_id']),
                "compatibility_score": sanitize_input(match['compatibility_score']),
                "reasons": [sanitize_input(reason) for reason in match.get('reasons', [])],
                "timestamp": sanitize_input(str(match['timestamp'])),
                "title": sanitize_input(match['title']),
                "brief_summary": sanitize_input(match['brief_summary']),
                "phase": [sanitize_input(phase) for phase in match['phase']],
                "status": sanitize_input(match['status'])
            }
            for match in matches
        ]

        return jsonify(sanitized_matches), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching recent matches for user {current_user}: {str(e)}")
        return handle_general_error(e)

@trial_matching.route('/start-match', methods=['POST'])
@jwt_required()
async def start_matching_process():
    current_user = get_jwt_identity()
    try:
        # Get the trial matching service from the current app context
        trial_matching_service = current_app.trial_matching_service
        # Start the matching process for the current user
        result = await trial_matching_service.start_matching_process(current_user)
        return jsonify(result), 202
    except Exception as e:
        return handle_general_error(e)

@trial_matching.route('/stop-match', methods=['POST'])
@jwt_required()
async def stop_matching_process():
    current_user = get_jwt_identity()
    try:
        # Get the trial matching service from the current app context
        trial_matching_service = current_app.trial_matching_service
        # Stop the matching process for the current user
        result = await trial_matching_service.stop_matching_process(current_user)
        return jsonify(result), 200
    except Exception as e:
        return handle_general_error(e)

@trial_matching.route('/match-status', methods=['GET'])
@jwt_required()
async def get_matching_status():
    current_user = get_jwt_identity()
    try:
        # Get the trial matching service from the current app context
        trial_matching_service = current_app.trial_matching_service
        # Get the current status of the matching process for the user
        status = await trial_matching_service.get_matching_status(current_user)
        return jsonify(status), 200
    except Exception as e:
        return handle_general_error(e)
    
@trial_matching.route('/all-matches', methods=['GET'])
@jwt_required()
async def get_all_matches():
    current_user = get_jwt_identity()
    try:
        # Get pagination parameters from the request
        page = int(sanitize_input(request.args.get('page', 1)))
        per_page = min(int(sanitize_input(request.args.get('per_page', 10))), 100)  # Limit max per_page to 100

        # Calculate skip value for pagination
        skip = (page - 1) * per_page

        db = await get_db()
        
        # Fetch total count of matches for the user
        total_matches = await db.trial_matches.count_documents({"user_id": current_user})

        # MongoDB aggregation pipeline to fetch paginated matches
        pipeline = [
            {"$match": {"user_id": current_user}},
            {"$sort": {"timestamp": -1}},
            {"$skip": skip},
            {"$limit": per_page},
            {
                "$lookup": {
                    "from": "clinical_trials",
                    "localField": "nct_id",
                    "foreignField": "nct_id",
                    "as": "trial_info"
                }
            },
            {"$unwind": "$trial_info"},
            {
                "$project": {
                    "nct_id": 1,
                    "compatibility_score": 1,
                    "reasons": 1,
                    "timestamp": 1,
                    "title": "$trial_info.brief_title",
                    "brief_summary": "$trial_info.brief_summary",
                    "phase": "$trial_info.phase",
                    "status": "$trial_info.status"
                }
            }
        ]

        # Execute the aggregation pipeline
        matches = await db.trial_matches.aggregate(pipeline).to_list(length=per_page)

        # Sanitize the output to prevent potential XSS or injection attacks
        sanitized_matches = [
            {
                "nct_id": sanitize_input(match['nct_id']),
                "compatibility_score": sanitize_input(match['compatibility_score']),
                "reasons": [sanitize_input(reason) for reason in match.get('reasons', [])],
                "timestamp": sanitize_input(str(match['timestamp'])),
                "title": sanitize_input(match['title']),
                "brief_summary": sanitize_input(match['brief_summary']),
                "phase": [sanitize_input(phase) for phase in match['phase']],
                "status": sanitize_input(match['status'])
            }
            for match in matches
        ]

        # Return paginated results along with metadata
        return jsonify({
            "matches": sanitized_matches,
            "total": total_matches,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_matches + per_page - 1) // per_page
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching all matches for user {current_user}: {str(e)}")
        return handle_general_error(e)