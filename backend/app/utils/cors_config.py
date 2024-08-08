# app/utils/cors_config.py

from flask_cors import CORS

def configure_cors(app):
    """
    Configure CORS for the Flask app with enhanced security and flexibility.
    
    Args:
        app (Flask): The Flask application instance.
    """
    CORS(app, resources={r"/api/*": {
        "origins": ["http://localhost:3000"],  # Add your frontend origin
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }})

    # Log CORS configuration
    app.logger.info("CORS configured with credentials support for allowed origins")