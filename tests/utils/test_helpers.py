"""
Tests for helper functions.
"""

from datetime import datetime

def test_get_ist_time():
    """Test the get_ist_time function."""
    from app import get_ist_time

    # Get IST time
    ist_time = get_ist_time()

    # Verify it's a datetime object
    assert isinstance(ist_time, datetime)

    # Verify it has timezone info
    assert ist_time.tzinfo is not None

    # Verify it's roughly IST (UTC+5:30)
    # We'll check if the offset is approximately 5 hours and 30 minutes
    offset = ist_time.utcoffset().total_seconds()
    expected_offset = 5 * 3600 + 30 * 60  # 5 hours and 30 minutes in seconds

    # Allow a small margin of error (1 second)
    assert abs(offset - expected_offset) <= 1

def test_get_settings():
    """Test the get_settings function."""
    from app import app, db, get_settings, Settings

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Clear any existing settings
        Settings.query.delete()
        db.session.commit()

        # Create settings
        settings = Settings(
            queue_active=True,
            current_token_id=0,
            last_token_number=0,
            use_thermal_printer=True
        )
        db.session.add(settings)
        db.session.commit()

        # Get settings
        retrieved_settings = get_settings()

        # Assertions
        assert retrieved_settings is not None
        assert retrieved_settings.queue_active is True
        assert retrieved_settings.current_token_id == 0
        assert retrieved_settings.last_token_number == 0
        assert retrieved_settings.use_thermal_printer is True

def test_format_token_number():
    """Test the format_token_number function if it exists."""
    # This is a placeholder - you'll need to adjust based on your actual implementation
    try:
        from app import format_token_number

        # Test with different numbers
        assert format_token_number(1) == 'A001'
        assert format_token_number(10) == 'A010'
        assert format_token_number(100) == 'A100'
    except ImportError:
        # If the function doesn't exist, skip this test
        print("Skipping test: format_token_number function not found in app")

def test_get_current_token():
    """Test the get_current_token function if it exists."""
    # This is a placeholder - you'll need to adjust based on your actual implementation
    try:
        from app import app, db, get_current_token, Token, Settings

        with app.app_context():
            # Create tables if they don't exist
            db.create_all()

            # Clear any existing data
            Token.query.delete()
            Settings.query.delete()
            db.session.commit()

            # Create settings with current_token_id
            settings = Settings(
                queue_active=True,
                current_token_id=1,
                last_token_number=1,
                use_thermal_printer=True
            )
            db.session.add(settings)

            # Create a token
            token = Token(
                id=1,
                token_number='A001',
                visit_reason='reason1',
                customer_name='Test Customer',
                status='SERVING'
            )
            db.session.add(token)
            db.session.commit()

            # Get current token
            current_token = get_current_token()

            # Assertions
            assert current_token is not None
            assert current_token.id == 1
            assert current_token.token_number == 'A001'
            assert current_token.status == 'SERVING'
    except ImportError:
        # If the function doesn't exist, skip this test
        print("Skipping test: get_current_token function not found in app")
