"""
Test runner script for QMS application.
Run this script to execute all tests.
"""

import os
import sys
import subprocess

def run_tests():
    """Run all tests."""
    print("Running QMS application tests...")

    # Add the current directory to the path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    # Run pytest using subprocess to avoid import issues
    try:
        subprocess.run([sys.executable, '-m', 'pytest', '-v', 'tests'], check=True)
        print("\nAll tests completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\nTests failed with exit code {e.returncode}")
        return e.returncode

if __name__ == '__main__':
    # Run the tests
    exit_code = run_tests()

    # Exit with the pytest result code
    sys.exit(exit_code)
