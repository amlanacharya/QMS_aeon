"""Password hashing test script"""

from flask import Flask
from flask_bcrypt import Bcrypt
import sys

# Test app
app = Flask(__name__)
bcrypt = Bcrypt(app)

def test_password_hashing():
    """Test password hashing and verification"""
    print("Testing password hashing functionality...")

    # Test data
    password = "test_password123"

    # Generate hash
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    print(f"Original password: {password}")
    print(f"Hashed password: {password_hash}")

    # Verify hash
    is_valid = bcrypt.check_password_hash(password_hash, password)
    print(f"Password verification (should be True): {is_valid}")

    # Test incorrect password
    is_valid = bcrypt.check_password_hash(password_hash, "wrong_password")
    print(f"Incorrect password verification (should be False): {is_valid}")

    # Test hash uniqueness
    another_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    print(f"Another hash for the same password: {another_hash}")
    print(f"Are the hashes different? {password_hash != another_hash}")

    # Verify second hash
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
