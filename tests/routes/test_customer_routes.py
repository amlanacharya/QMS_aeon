"""
Tests for customer-facing routes.
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_index_route():
    """Test the index route."""
    from app import app, db, Settings

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Create a settings record if it doesn't exist
        if not Settings.query.first():
            settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
            db.session.add(settings)
            db.session.commit()

    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'Queue Management System' in response.data

def test_generate_token_form():
    """Test the token generation form on the home page."""
    from app import app, db, Settings

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Create a settings record if it doesn't exist
        if not Settings.query.first():
            settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
            db.session.add(settings)
            db.session.commit()

    with app.test_client() as client:
        # The form is on the home page
        response = client.get('/')
        assert response.status_code == 200
        # Check for form elements related to token generation
        assert b'form' in response.data.lower() and b'submit' in response.data.lower()

def test_token_status_display():
    """Test the token status display on the home page."""
    from app import app, db, Settings

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Create a settings record if it doesn't exist
        if not Settings.query.first():
            settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
            db.session.add(settings)
            db.session.commit()

    with app.test_client() as client:
        # The token status is displayed on the home page
        response = client.get('/')
        assert response.status_code == 200
        # Check for token status elements
        assert b'NOW SERVING' in response.data or b'now serving' in response.data.lower()

def test_generate_token_submission():
    """Test submitting the token generation form."""
    from app import app, db, Reason, Token, Settings

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Create a settings record if it doesn't exist
        if not Settings.query.first():
            settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
            db.session.add(settings)
            db.session.commit()

        # Add a test reason if it doesn't exist
        if not Reason.query.filter_by(code='test_reason').first():
            reason = Reason(code='test_reason', description='Test Reason')
            db.session.add(reason)
            db.session.commit()

    with app.test_client() as client:
        # Submit the form
        response = client.post('/generate-token', data={
            'visit_reason': 'test_reason',
            'customer_name': 'Test Customer',
            'phone_number': '1234567890'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Token generated successfully' in response.data or b'token' in response.data.lower()

        # Check that the token was created
        with app.app_context():
            token = Token.query.filter_by(customer_name='Test Customer').first()
            assert token is not None
            assert token.visit_reason == 'test_reason'
            assert token.phone_number == '1234567890'
            assert token.status == 'PENDING'
