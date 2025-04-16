import sys
import os

# Add the application directory to the Python path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Import the Flask application
from app import app as application

# PythonAnywhere uses WSGI to serve the application
# This file is the entry point for the WSGI server
