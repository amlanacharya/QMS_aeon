import sys
import os

# Add app directory to path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Import Flask app
from app import app as application

# WSGI entry point
