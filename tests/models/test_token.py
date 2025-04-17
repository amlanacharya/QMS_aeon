"""
Tests for the Token model.
"""

import pytest
from datetime import datetime, timedelta

def test_token_creation(app, db):
    """Test creating a new token."""
    from app import Token
    
    with app.app_context():
        # Create a new token
        token = Token(
            token_number='T001',
            visit_reason='reason1',
            customer_name='Test Customer',
            phone_number='1234567890',
            status='PENDING'
        )
        
        db.session.add(token)
        db.session.commit()
        
        # Retrieve the token
        saved_token = Token.query.filter_by(token_number='T001').first()
        
        # Assertions
        assert saved_token is not None
        assert saved_token.token_number == 'T001'
        assert saved_token.visit_reason == 'reason1'
        assert saved_token.customer_name == 'Test Customer'
        assert saved_token.phone_number == '1234567890'
        assert saved_token.status == 'PENDING'
        assert saved_token.created_at is not None
        assert saved_token.recall_count == 0
        assert saved_token.skip_count == 0

def test_token_status_update(app, db):
    """Test updating token status."""
    from app import Token
    
    with app.app_context():
        # Create a new token
        token = Token(
            token_number='T002',
            visit_reason='reason1',
            customer_name='Test Customer',
            status='PENDING'
        )
        
        db.session.add(token)
        db.session.commit()
        
        # Update status to SERVING
        token.status = 'SERVING'
        token.served_at = datetime.now()
        db.session.commit()
        
        # Retrieve the token
        updated_token = Token.query.filter_by(token_number='T002').first()
        
        # Assertions
        assert updated_token.status == 'SERVING'
        assert updated_token.served_at is not None
        
        # Update status to COMPLETED
        updated_token.status = 'COMPLETED'
        updated_token.completed_at = datetime.now()
        updated_token.service_duration = 300  # 5 minutes
        db.session.commit()
        
        # Retrieve the token again
        completed_token = Token.query.filter_by(token_number='T002').first()
        
        # Assertions
        assert completed_token.status == 'COMPLETED'
        assert completed_token.completed_at is not None
        assert completed_token.service_duration == 300

def test_token_recall(app, db):
    """Test token recall functionality."""
    from app import Token
    
    with app.app_context():
        # Create a new token
        token = Token(
            token_number='T003',
            visit_reason='reason1',
            customer_name='Test Customer',
            status='SERVING'
        )
        
        db.session.add(token)
        db.session.commit()
        
        # Recall the token
        token.status = 'RECALLED'
        token.recall_count += 1
        token.last_recalled_at = datetime.now()
        db.session.commit()
        
        # Retrieve the token
        recalled_token = Token.query.filter_by(token_number='T003').first()
        
        # Assertions
        assert recalled_token.status == 'RECALLED'
        assert recalled_token.recall_count == 1
        assert recalled_token.last_recalled_at is not None

def test_token_skip(app, db):
    """Test token skip functionality."""
    from app import Token
    
    with app.app_context():
        # Create a new token
        token = Token(
            token_number='T004',
            visit_reason='reason1',
            customer_name='Test Customer',
            status='SERVING'
        )
        
        db.session.add(token)
        db.session.commit()
        
        # Skip the token
        token.status = 'SKIPPED'
        token.skip_count += 1
        token.last_skipped_at = datetime.now()
        token.previous_status = 'SERVING'
        db.session.commit()
        
        # Retrieve the token
        skipped_token = Token.query.filter_by(token_number='T004').first()
        
        # Assertions
        assert skipped_token.status == 'SKIPPED'
        assert skipped_token.skip_count == 1
        assert skipped_token.last_skipped_at is not None
        assert skipped_token.previous_status == 'SERVING'
