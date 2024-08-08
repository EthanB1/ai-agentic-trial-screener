# run.py

import os
from app import create_app
from flask.cli import FlaskGroup

app = create_app()

# Create a Flask CLI group
cli = FlaskGroup(app)

if __name__ == "__main__":
    try:
        # Get the port from environment variable or use 5000 as default
        port = int(os.environ.get("PORT", 5000))
        
        # Run the app with debug mode enabled
        app.run(debug=True, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"An error occurred while starting the server: {e}")
    finally:
        print("Server shutting down...")