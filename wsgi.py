#!/usr/bin/env python3
"""
WSGI entry point for Gunicorn deployment
"""

from app import app

# Expose the Flask server
server = app.server
application = app.server

if __name__ == "__main__":
    server.run() 
