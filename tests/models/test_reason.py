"""
Tests for the Reason model.
"""

import pytest
from datetime import datetime

def test_reason_creation(app, db):
    """Test creating a new reason."""
    from app import Reason
    
    with app.app_context():
        # Create a new reason
        reason = Reason(
            code='test_reason',
            description='Test Reason Description',
            is_active=True
        )
        
        db.session.add(reason)
        db.session.commit()
        
        # Retrieve the reason
        saved_reason = Reason.query.filter_by(code='test_reason').first()
        
        # Assertions
        assert saved_reason is not None
        assert saved_reason.code == 'test_reason'
        assert saved_reason.description == 'Test Reason Description'
        assert saved_reason.is_active is True
        assert saved_reason.created_at is not None
        assert saved_reason.updated_at is not None

def test_reason_update(app, db):
    """Test updating a reason."""
    from app import Reason
    
    with app.app_context():
        # Create a new reason
        reason = Reason(
            code='update_reason',
            description='Original Description',
            is_active=True
        )
        
        db.session.add(reason)
        db.session.commit()
        
        # Store the original timestamps
        original_created_at = reason.created_at
        original_updated_at = reason.updated_at
        
        # Wait a moment to ensure timestamps would be different
        import time
        time.sleep(0.1)
        
        # Update the reason
        reason.description = 'Updated Description'
        reason.is_active = False
        db.session.commit()
        
        # Retrieve the updated reason
        updated_reason = Reason.query.filter_by(code='update_reason').first()
        
        # Assertions
        assert updated_reason.description == 'Updated Description'
        assert updated_reason.is_active is False
        assert updated_reason.created_at == original_created_at  # Should not change
        assert updated_reason.updated_at > original_updated_at  # Should be updated

def test_reason_uniqueness(app, db):
    """Test that reason codes must be unique."""
    from app import Reason
    from sqlalchemy.exc import IntegrityError
    
    with app.app_context():
        # Create a reason
        reason1 = Reason(
            code='unique_reason',
            description='First Reason',
            is_active=True
        )
        
        db.session.add(reason1)
        db.session.commit()
        
        # Try to create another reason with the same code
        reason2 = Reason(
            code='unique_reason',  # Same code as reason1
            description='Second Reason',
            is_active=True
        )
        
        db.session.add(reason2)
        
        # This should raise an IntegrityError
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        # Rollback the session
        db.session.rollback()
