# app/routes/__init__.py
from flask import Blueprint, jsonify
from .auth import auth
from .patient import patient
from .trial_matching import trial_matching


def register_routes(app):
    """
    Register all blueprint routes with the app.
    
    Args:
        app: The Flask application instance.
    """
    app.register_blueprint(auth, url_prefix='/api/auth')
    app.register_blueprint(patient, url_prefix='/api/patient')
    app.register_blueprint(trial_matching, url_prefix='/api/trial-matching')

    