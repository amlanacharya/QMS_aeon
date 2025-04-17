"""
Basic tests for the QMS application.
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_app_creation():
    """Test that the app can be created."""
    from app import app
    assert app is not None

def test_db_connection():
    """Test that the database connection works."""
    from app import db
    assert db is not None

def test_index_route():
    """Test the index route."""
    from app import app, db

    # Create tables first
    with app.app_context():
        db.create_all()

        # Create a settings record if it doesn't exist
        from app import Settings
        if not Settings.query.first():
            settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
            db.session.add(settings)
            db.session.commit()

    # Now test the route
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'Queue Management System' in response.data

def test_print_test_simple():
    """Test the simple print test endpoint."""
    from app import app
    with app.test_client() as client:
        response = client.get('/api/print-test-simple')
        assert response.status_code == 200

        # Check the response is JSON
        assert response.content_type == 'application/json'

        # Parse the JSON
        data = response.get_json()

        # Check the structure
        assert "0" in data
        assert data["0"]["type"] == 0
        assert "content" in data["0"]
        assert "bold" in data["0"]
        assert "align" in data["0"]
