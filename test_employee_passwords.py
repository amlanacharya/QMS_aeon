"""
Test script for employee password functionality.
This script tests the password hashing implementation with the Employee model.
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Create a simple Flask app for testing
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tokens.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Define a simplified Employee model for testing
class Employee(db.Model):
    __tablename__ = 'employee'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    
    def set_password(self, password):
        """Set the password (hashes it)."""
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check the password."""
        return bcrypt.check_password_hash(self.password, password)

def test_create_employee():
    """Test creating an employee with a hashed password."""
    print("\n1. Testing employee creation with hashed password...")
    
    # Create a test employee
    test_employee = Employee(
        employee_id="test_user",
        name="Test User"
    )
    
    # Set a hashed password
    test_password = "test_password123"
    test_employee.set_password(test_password)
    
    print(f"Employee ID: {test_employee.employee_id}")
    print(f"Name: {test_employee.name}")
    print(f"Hashed password: {test_employee.password}")
    
    # Verify the password
    is_valid = test_employee.check_password(test_password)
    print(f"Password verification (should be True): {is_valid}")
    
    # Try an incorrect password
    is_valid = test_employee.check_password("wrong_password")
    print(f"Incorrect password verification (should be False): {is_valid}")
    
    return test_employee

def test_existing_employees():
    """Test password verification with existing employees."""
    print("\n2. Testing existing employees in the database...")
    
    # Get all employees
    employees = Employee.query.all()
    
    if not employees:
        print("No employees found in the database.")
        return
    
    print(f"Found {len(employees)} employees in the database.")
    
    for employee in employees:
        print(f"\nEmployee ID: {employee.employee_id}")
        print(f"Name: {employee.name}")
        print(f"Current password hash: {employee.password}")
        
        # Check if the password is already hashed
        is_hashed = employee.password.startswith('$2b$') or employee.password.startswith('$2a$')
        print(f"Is password hashed? {is_hashed}")
        
        if not is_hashed:
            print("This employee has a plaintext password. Let's hash it.")
            
            # Store the plaintext password
            plaintext = employee.password
            
            # Hash the password
            employee.set_password(plaintext)
            print(f"New hashed password: {employee.password}")
            
            # Verify the password
            is_valid = employee.check_password(plaintext)
            print(f"Password verification after hashing (should be True): {is_valid}")
        else:
            print("This employee already has a hashed password.")

def main():
    """Run all tests."""
    print("Starting password functionality tests...")
    
    with app.app_context():
        # Test creating an employee
        test_employee = test_create_employee()
        
        # Test existing employees
        test_existing_employees()
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        sys.exit(1)
