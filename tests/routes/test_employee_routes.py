"""
Tests for employee routes.
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_employee_login_page():
    """Test the employee login page."""
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
        response = client.get('/employee-login')
        assert response.status_code == 200
        assert b'Employee Login' in response.data or b'employee login' in response.data.lower()

def test_employee_login():
    """Test employee login functionality."""
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
        employee = Employee.query.filter_by(employee_id='test_emp').first()
        if not employee:
            employee = Employee(employee_id='test_emp', name='Test Employee', role='employee')
            employee.set_password('password123')
            db.session.add(employee)
            db.session.commit()

    with app.test_client() as client:
        # Test login with correct credentials
        response = client.post('/employee-login-process', data={
            'employee_id': 'test_emp',
            'password': 'password123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Employee Dashboard' in response.data or b'employee' in response.data.lower()

        # Test login with incorrect password
        response = client.post('/employee-login-process', data={
            'employee_id': 'test_emp',
            'password': 'wrong_password'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Invalid credentials' in response.data or b'invalid' in response.data.lower()

        # Test login with non-existent employee
        response = client.post('/employee-login-process', data={
            'employee_id': 'nonexistent',
            'password': 'password123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Invalid credentials' in response.data or b'invalid' in response.data.lower()

def test_employee_dashboard_access():
    """Test access to employee dashboard."""
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
        employee = Employee.query.filter_by(employee_id='test_emp2').first()
        if not employee:
            employee = Employee(employee_id='test_emp2', name='Test Employee 2', role='employee')
            employee.set_password('password123')
            db.session.add(employee)
            db.session.commit()

        # Get the employee ID to use in the session
        employee_id = employee.id

    with app.test_client() as client:
        # Try to access dashboard without login
        response = client.get('/employee-dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'Please log in' in response.data or b'login' in response.data.lower()

        # Login
        with client.session_transaction() as sess:
            sess['employee_id'] = employee_id

        # Access dashboard after login
        response = client.get('/employee-dashboard')
        assert response.status_code == 200
        assert b'Employee Dashboard' in response.data or b'employee' in response.data.lower()

def test_employee_logout():
    """Test employee logout functionality."""
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
        employee = Employee.query.filter_by(employee_id='test_emp3').first()
        if not employee:
            employee = Employee(employee_id='test_emp3', name='Test Employee 3', role='employee')
            employee.set_password('password123')
            db.session.add(employee)
            db.session.commit()

        # Get the employee ID to use in the session
        employee_id = employee.id

    with app.test_client() as client:
        # Login
        with client.session_transaction() as sess:
            sess['employee_id'] = employee_id

        # Logout
        response = client.get('/employee-logout', follow_redirects=True)
        assert response.status_code == 200
        # The response might not explicitly say 'logged out', so just check we're redirected to the home page
        assert b'Queue Management System' in response.data or b'QMS' in response.data

        # Try to access dashboard after logout
        response = client.get('/employee-dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'Please log in' in response.data or b'login' in response.data.lower()
