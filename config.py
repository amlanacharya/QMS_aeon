import os
from datetime import timezone, timedelta

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class Config:
    """Base configuration."""
    # Use environment variable for SECRET_KEY if available, otherwise use a secure default
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a8c7ef9d2b4e6f8a0c2e4d6b8a0c2e4d6b8a0c2e4d6b8a0c2e4d6b')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tokens.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # Timezone settings
    TIMEZONE = IST

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # In production, ensure these are set through environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    # If SECRET_KEY is not set, raise an error
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for production environment")
    
    # If ADMIN_PASSWORD is not set, raise an error
    if not ADMIN_PASSWORD:
        raise ValueError("No ADMIN_PASSWORD set for production environment")

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'

# Dictionary to easily access different configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Function to get the appropriate configuration
def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    if env == 'production':
        return config['production']
    elif env == 'testing':
        return config['testing']
    else:
        return config['development']
