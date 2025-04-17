"""
Tests for printing functionality.
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_print_test_simple():
    """Test the simple print test endpoint."""
    from app import app
    with app.test_client() as client:
        response = client.get('/api/print-test-simple')
        assert response.status_code == 200

        # Check the response is JSON
        assert response.content_type == 'application/json'

        # Parse the JSON
        data = response.get_json()

        # Check the structure
        assert "0" in data
        assert data["0"]["type"] == 0
        assert "content" in data["0"]
        assert "bold" in data["0"]
        assert "align" in data["0"]

def test_print_test_json():
    """Test the full print test endpoint."""
    from app import app
    with app.test_client() as client:
        response = client.get('/api/print-test')
        assert response.status_code == 200

        # Check the response is JSON
        assert response.content_type == 'application/json'

        # Parse the JSON
        data = response.get_json()

        # Check the structure
        assert len(data) > 0

        # Check a few specific entries
        assert "0" in data
        assert data["0"]["type"] == 0
        assert "Printer Test" in data["0"]["content"]

        # Check that we have different formatting options
        formats_found = set()
        aligns_found = set()
        bold_values = set()

        for key in data:
            if "format" in data[key]:
                formats_found.add(data[key]["format"])
            if "align" in data[key]:
                aligns_found.add(data[key]["align"])
            if "bold" in data[key]:
                bold_values.add(data[key]["bold"])

        # We should have at least one of each format type
        assert len(formats_found) > 0
        assert len(aligns_found) > 0
        assert len(bold_values) > 0

def test_print_exact_test():
    """Test the exact print test endpoint."""
    from app import app
    with app.test_client() as client:
        response = client.get('/api/print-exact-test')
        assert response.status_code == 200

        # Check the response is JSON
        assert response.content_type == 'application/json'

        # Parse the JSON
        data = response.get_json()

        # Check the structure
        assert "0" in data
        assert "1" in data

        # Check the title
        assert data["0"]["content"] == "My Title"
        assert data["0"]["bold"] == 1
        assert data["0"]["align"] == 2
        assert data["0"]["format"] == 3

        # Check the spacing
        assert data["1"]["content"] == " "
        assert data["1"]["bold"] == 0
        assert data["1"]["align"] == 0

def test_print_token_static():
    """Test the static token print endpoint."""
    from app import app
    with app.test_client() as client:
        response = client.get('/api/print-token-static/123')
        assert response.status_code == 200

        # Check the response is JSON
        assert response.content_type == 'application/json'

        # Parse the JSON
        data = response.get_json()

        # Check the structure
        assert len(data) > 0

        # Check that the token number is included
        token_found = False
        for key in data:
            if "content" in data[key] and "123" in data[key]["content"]:
                token_found = True
                break

        assert token_found, "Token number not found in the print data"
