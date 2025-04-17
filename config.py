import os
from datetime import timezone, timedelta

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

class Config:
    """Base config"""
    # App settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a8c7ef9d2b4e6f8a0c2e4d6b8a0c2e4d6b8a0c2e4d6b8a0c2e4d6b')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tokens.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

    # Timezone
    TIMEZONE = IST

class DevelopmentConfig(Config):
    """Dev config"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Prod config"""
    DEBUG = False
    TESTING = False

    # Required env vars
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

    # Validate SECRET_KEY
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for production environment")

    # Validate ADMIN_PASSWORD
    if not ADMIN_PASSWORD:
        raise ValueError("No ADMIN_PASSWORD set for production environment")

class TestingConfig(Config):
    """Test config"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'

# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Get config
def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    if env == 'production':
        return config['production']
    elif env == 'testing':
        return config['testing']
    else:
        return config['development']
