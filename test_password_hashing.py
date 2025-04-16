"""
Test script for password hashing functionality.
This script tests the bcrypt password hashing implementation.
"""

from flask import Flask
from flask_bcrypt import Bcrypt
import sys

# Create a simple Flask app for testing
app = Flask(__name__)
bcrypt = Bcrypt(app)

def test_password_hashing():
    """Test the password hashing and verification functionality."""
    print("Testing password hashing functionality...")
    
    # Test password
    password = "test_password123"
    
    # Generate a hash
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    print(f"Original password: {password}")
    print(f"Hashed password: {password_hash}")
    
    # Verify the hash
    is_valid = bcrypt.check_password_hash(password_hash, password)
    print(f"Password verification (should be True): {is_valid}")
    
    # Try an incorrect password
    is_valid = bcrypt.check_password_hash(password_hash, "wrong_password")
    print(f"Incorrect password verification (should be False): {is_valid}")
    
    # Generate another hash for the same password
    another_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    print(f"Another hash for the same password: {another_hash}")
    print(f"Are the hashes different? {password_hash != another_hash}")
    
    # Verify the second hash
    is_valid = bcrypt.check_password_hash(another_hash, password)
    print(f"Second hash verification (should be True): {is_valid}")
    
    print("\nAll tests completed successfully!")
    return True

if __name__ == "__main__":
    try:
        test_password_hashing()
        sys.exit(0)
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        sys.exit(1)
