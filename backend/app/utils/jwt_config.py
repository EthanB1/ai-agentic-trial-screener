# app/utils/jwt_config.py

from flask_jwt_extended import JWTManager
from datetime import timedelta
import os

def configure_jwt(app):
    # Ensure JWT secret key is set
    if not app.config.get('JWT_SECRET_KEY'):
        app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'default-secret-key'
    
    # Configure JWT settings
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    
    jwt = JWTManager(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'message': 'Token has expired'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'message': 'Invalid token'}, 401
    
    return jwt