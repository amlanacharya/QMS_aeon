"""
Tests for the Employee model.
"""

import pytest
from datetime import datetime, timedelta

def test_employee_creation(app, db):
    """Test creating a new employee."""
    from app import Employee

    with app.app_context():
        # Create a new employee
        employee = Employee(
            employee_id='emp001',
            name='John Doe',
            role='employee',
            is_active=True
        )

        # Set password
        employee.set_password('password123')

        db.session.add(employee)
        db.session.commit()

        # Retrieve the employee
        saved_employee = Employee.query.filter_by(employee_id='emp001').first()

        # Assertions
        assert saved_employee is not None
        assert saved_employee.employee_id == 'emp001'
        assert saved_employee.name == 'John Doe'
        assert saved_employee.role == 'employee'
        assert saved_employee.is_active is True
        assert saved_employee.created_at is not None
        assert saved_employee.tokens_served == 0
        assert saved_employee.avg_service_time == 0.0

def test_employee_password(app, db):
    """Test employee password hashing and verification."""
    from app import Employee

    with app.app_context():
        # Create a new employee
        employee = Employee(
            employee_id='emp002',
            name='Jane Smith',
            role='employee'
        )

        # Set password
        test_password = 'secure_password123'
        employee.set_password(test_password)

        db.session.add(employee)
        db.session.commit()

        # Retrieve the employee
        saved_employee = Employee.query.filter_by(employee_id='emp002').first()

        # Assertions
        assert saved_employee.password != test_password  # Password should be hashed
        assert saved_employee.check_password(test_password) is True  # Correct password
        assert saved_employee.check_password('wrong_password') is False  # Wrong password

def test_employee_stats_update(app, db):
    """Test updating employee statistics."""
    from app import Employee

    with app.app_context():
        # Create a new employee
        employee = Employee(
            employee_id='emp003',
            name='Alex Johnson',
            role='employee',
            tokens_served=0,
            avg_service_time=0.0
        )

        employee.set_password('password123')

        db.session.add(employee)
        db.session.commit()

        # Update stats after serving first token (5 minutes)
        employee.tokens_served = 1
        employee.avg_service_time = 5.0
        db.session.commit()

        # Retrieve the employee
        updated_employee = Employee.query.filter_by(employee_id='emp003').first()

        # Assertions
        assert updated_employee.tokens_served == 1
        assert updated_employee.avg_service_time == 5.0

        # Update stats after serving second token (10 minutes)
        # New average should be (5 + 10) / 2 = 7.5
        updated_employee.tokens_served = 2
        updated_employee.avg_service_time = 7.5
        db.session.commit()

        # Retrieve the employee again
        employee_after_second = Employee.query.filter_by(employee_id='emp003').first()

        # Assertions
        assert employee_after_second.tokens_served == 2
        assert employee_after_second.avg_service_time == 7.5

def test_employee_duty_status(app, db):
    """Test employee duty status."""
    from app import Employee

    with app.app_context():
        # Create a new employee
        employee = Employee(
            employee_id='emp004',
            name='Sam Wilson',
            role='employee',
            is_on_duty=False
        )

        employee.set_password('password123')

        db.session.add(employee)
        db.session.commit()

        # Update duty status
        employee.is_on_duty = True
        employee.last_login = datetime.now()
        db.session.commit()

        # Retrieve the employee
        updated_employee = Employee.query.filter_by(employee_id='emp004').first()

        # Assertions
        assert updated_employee.is_on_duty is True
        assert updated_employee.last_login is not None
