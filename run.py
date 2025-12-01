#!/usr/bin/env python3
"""
Badminton Tracker - Entry Point
"""

import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'

    if debug:
        # Development mode
        app.run(host=host, port=port, debug=True)
    else:
        # Production mode - use gunicorn
        # This block is for direct python run.py execution
        # In Docker, we use gunicorn directly
        app.run(host=host, port=port, debug=False)