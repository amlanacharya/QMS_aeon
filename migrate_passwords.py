#!/usr/bin/env python3
"""
Password Migration Script for QMS

This script migrates plaintext passwords to bcrypt hashed passwords.
Run this script after upgrading to the version that uses password hashing.
"""

import os
import sys
from flask_bcrypt import Bcrypt
from app import app, db, Employee

def migrate_passwords():
    """Migrate all plaintext passwords to hashed passwords."""
    print("Starting password migration...")
    
    # Initialize Bcrypt
    bcrypt = Bcrypt(app)
    
    # Get all employees
    employees = Employee.query.all()
    
    # Count for reporting
    total = len(employees)
    migrated = 0
    
    print(f"Found {total} employee accounts to migrate.")
    
    for employee in employees:
        # Check if the password is already hashed
        # Bcrypt hashes start with $2b$
        if employee.password.startswith('$2b$'):
            print(f"Employee {employee.employee_id} already has a hashed password. Skipping.")
            continue
        
        # Store the plaintext password temporarily
        plaintext = employee.password
        
        # Hash the password
        hashed = bcrypt.generate_password_hash(plaintext).decode('utf-8')
        
        # Update the employee record
        employee.password = hashed
        migrated += 1
        
        print(f"Migrated password for employee {employee.employee_id}")
    
    # Commit all changes
    db.session.commit()
    
    print(f"Migration complete. {migrated} of {total} passwords were migrated.")
    print("All passwords are now securely hashed.")

if __name__ == "__main__":
    # Check if we're in production mode
    if os.environ.get('PRODUCTION', 'False').lower() == 'true':
        confirm = input("You are running this script in PRODUCTION mode. Are you sure you want to continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(0)
    
    # Run the migration
    with app.app_context():
        migrate_passwords()
