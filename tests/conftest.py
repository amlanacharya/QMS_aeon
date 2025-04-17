"""
Test configuration for the QMS application.
This file contains fixtures and configuration for pytest.
"""

import os
import sys
import pytest
from datetime import timezone, timedelta

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create a test configuration class directly to avoid importing from config.py
class TestConfig:
    """Test configuration"""
    TESTING = True
    DEBUG = True
    SECRET_KEY = 'test_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_PASSWORD = 'test_admin_password'
    TIMEZONE = timezone(timedelta(hours=5, minutes=30))  # IST

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Import the app from the main module
    from app import app as flask_app

    # Override the configuration
    flask_app.config.from_object(TestConfig)

    # Create all tables
    with flask_app.app_context():
        from app import db
        db.create_all()

    yield flask_app

    # Clean up / reset resources
    with flask_app.app_context():
        from app import db
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def db(app):
    """Get the SQLAlchemy database instance."""
    from app import db as _db
    with app.app_context():
        yield _db

@pytest.fixture
def init_database(app, db):
    """Initialize the database with test data."""
    from app import Token, Employee, Reason, Settings

    # Create test settings
    settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
    db.session.add(settings)

    # Create test reasons
    reasons = [
        Reason(code='reason1', description='Test Reason 1'),
        Reason(code='reason2', description='Test Reason 2'),
        Reason(code='reason3', description='Test Reason 3')
    ]
    db.session.add_all(reasons)

    # Create test employee
    employee = Employee(employee_id='test_emp', name='Test Employee', role='employee')
    employee.set_password('password123')
    db.session.add(employee)

    # Create admin employee
    admin = Employee(employee_id='admin', name='Admin User', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)

    # Create test tokens
    tokens = [
        Token(token_number='A001', visit_reason='reason1', customer_name='Customer 1', status='PENDING'),
        Token(token_number='A002', visit_reason='reason2', customer_name='Customer 2', status='SERVING'),
        Token(token_number='A003', visit_reason='reason3', customer_name='Customer 3', status='COMPLETED')
    ]
    db.session.add_all(tokens)

    db.session.commit()

    yield db

    # Clean up
    db.session.query(Token).delete()
    db.session.query(Employee).delete()
    db.session.query(Reason).delete()
    db.session.query(Settings).delete()
    db.session.commit()
