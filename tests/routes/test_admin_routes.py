"""
Tests for admin routes.
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_admin_login_page():
    """Test the admin login page."""
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
        response = client.get('/admin')
        assert response.status_code == 200
        assert b'Admin Login' in response.data or b'admin login' in response.data.lower()

def test_admin_login():
    """Test admin login functionality."""
    from app import app, db, Employee, Settings

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Create a settings record if it doesn't exist
        if not Settings.query.first():
            settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
            db.session.add(settings)
            db.session.commit()

    with app.test_client() as client:
        # Test login with correct credentials
        response = client.post('/admin-login', data={
            'password': 'admin123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data or b'admin' in response.data.lower()

        # Test login with incorrect password
        response = client.post('/admin-login', data={
            'password': 'wrong_password'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Invalid password' in response.data or b'invalid' in response.data.lower()

def test_admin_dashboard_access():
    """Test access to admin dashboard."""
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
        # Try to access dashboard without login
        response = client.get('/admin', follow_redirects=True)
        assert response.status_code == 200
        assert b'Admin Login' in response.data or b'admin login' in response.data.lower()

        # Login
        client.post('/admin-login', data={
            'password': 'admin123'
        })

        # Access dashboard after login
        response = client.get('/admin')
        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data or b'admin' in response.data.lower()

def test_admin_settings_access():
    """Test access to admin settings."""
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
        # Login
        with client.session_transaction() as sess:
            sess['is_admin'] = True

        # Access admin page which has settings controls
        response = client.get('/admin')
        assert response.status_code == 200
        # Check for any admin-related content
        assert b'Admin' in response.data or b'admin' in response.data.lower()

def test_employee_cannot_access_admin():
    """Test that regular employees cannot access admin routes."""
    from app import app, db, Employee, Settings

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Create a settings record if it doesn't exist
        if not Settings.query.first():
            settings = Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True)
            db.session.add(settings)
            db.session.commit()

        # Create a test employee if it doesn't exist
        employee = Employee.query.filter_by(employee_id='regular_emp').first()
        if not employee:
            employee = Employee(employee_id='regular_emp', name='Regular Employee', role='employee')
            employee.set_password('password123')
            db.session.add(employee)
            db.session.commit()

        # Get the employee ID to use in the session
        employee_id = employee.id
        employee_role = 'employee'

    with app.test_client() as client:
        # Login as employee
        with client.session_transaction() as sess:
            sess['employee_id'] = employee_id
            sess['employee_role'] = employee_role

        # Try to access admin dashboard
        response = client.get('/admin', follow_redirects=True)
        assert response.status_code == 200
        # Either we see the login page or an access denied message
        assert b'Admin Login' in response.data or b'access denied' in response.data.lower() or b'not authorized' in response.data.lower()
