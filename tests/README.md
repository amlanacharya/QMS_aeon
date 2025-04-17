# QMS Application Tests

This directory contains tests for the QMS (Queue Management System) application.

## Test Structure

The tests are organized into the following directories:

- `models/`: Tests for database models
- `routes/`: Tests for application routes and views
- `utils/`: Tests for utility functions and helpers

## Running Tests

You can run the tests using the `run_tests.py` script in the root directory:

```
python run_tests.py
```

Or you can use pytest directly:

```
pytest -v tests
```

## Test Configuration

There are two approaches to testing in this project:

1. **Direct Import Approach**: Most tests use direct imports from the application. This approach is simpler and more reliable, as it uses the actual application instance.

2. **Fixture-Based Approach**: Some tests use pytest fixtures defined in `conftest.py`. This approach is useful for more complex tests that require a controlled environment.

## Writing New Tests

When writing new tests, follow these guidelines:

1. Place the test in the appropriate directory based on what you're testing
2. Use descriptive test names that clearly indicate what is being tested
3. For simple tests, use the direct import approach:
   ```python
   def test_something():
       from app import app
       with app.test_client() as client:
           # Test code here
   ```
4. For more complex tests, use pytest fixtures if needed
5. Clean up after tests to avoid affecting other tests

## Test Coverage

To generate a test coverage report, install pytest-cov and run:

```
pytest --cov=app tests/
```

This will show which parts of the application are covered by tests and which are not.
