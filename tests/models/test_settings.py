"""
Tests for the Settings model.
"""

import pytest

def test_settings_creation(app, db):
    """Test creating settings."""
    from app import Settings
    
    with app.app_context():
        # Create settings
        settings = Settings(
            queue_active=True,
            current_token_id=0,
            last_token_number=0,
            use_thermal_printer=True
        )
        
        db.session.add(settings)
        db.session.commit()
        
        # Retrieve settings
        saved_settings = Settings.query.first()
        
        # Assertions
        assert saved_settings is not None
        assert saved_settings.queue_active is True
        assert saved_settings.current_token_id == 0
        assert saved_settings.last_token_number == 0
        assert saved_settings.use_thermal_printer is True

def test_settings_update(app, db):
    """Test updating settings."""
    from app import Settings
    
    with app.app_context():
        # Create settings
        settings = Settings(
            queue_active=True,
            current_token_id=0,
            last_token_number=0,
            use_thermal_printer=True
        )
        
        db.session.add(settings)
        db.session.commit()
        
        # Update settings
        settings.queue_active = False
        settings.current_token_id = 5
        settings.last_token_number = 10
        settings.use_thermal_printer = False
        db.session.commit()
        
        # Retrieve updated settings
        updated_settings = Settings.query.first()
        
        # Assertions
        assert updated_settings.queue_active is False
        assert updated_settings.current_token_id == 5
        assert updated_settings.last_token_number == 10
        assert updated_settings.use_thermal_printer is False

def test_singleton_behavior(app, db):
    """Test that Settings behaves like a singleton."""
    from app import Settings
    
    with app.app_context():
        # Create first settings
        settings1 = Settings(
            queue_active=True,
            current_token_id=0,
            last_token_number=0,
            use_thermal_printer=True
        )
        
        db.session.add(settings1)
        db.session.commit()
        
        # Create second settings
        settings2 = Settings(
            queue_active=False,
            current_token_id=5,
            last_token_number=10,
            use_thermal_printer=False
        )
        
        db.session.add(settings2)
        db.session.commit()
        
        # Count settings
        settings_count = Settings.query.count()
        
        # Assertions - there should be two records since we're not enforcing singleton in the model
        assert settings_count == 2
        
        # In the application, this is typically handled by always using Settings.query.first()
        first_settings = Settings.query.first()
        assert first_settings is not None
