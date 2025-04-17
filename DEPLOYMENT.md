# Deployment Guide for QMS System

This guide provides instructions for deploying the QMS (Queue Management System) application to a production environment, specifically on PythonAnywhere.

## Prerequisites

- A PythonAnywhere account
- Git installed on your local machine
- Access to the QMS repository

## Deployment Steps

### 1. Clone the Repository on PythonAnywhere

1. Log in to your PythonAnywhere account
2. Open a Bash console
3. Clone the repository:
   ```
   git clone https://github.com/amlanacharya/QMS_aeon.git
   cd QMS_aeon
   ```

### 2. Set Up a Virtual Environment

1. Create a virtual environment:
   ```
   mkvirtualenv --python=/usr/bin/python3.9 qms_env
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### 3. Configure Environment Variables

Set the following environment variables in the PythonAnywhere dashboard under the "Web" tab, in the "Environment variables" section:

- `SECRET_KEY`: A secure random string for Flask session encryption
- `ADMIN_PASSWORD`: A secure password for admin access
- `PRODUCTION`: Set to "True" for production mode
- `DATABASE_URL`: (Optional) If using a different database than SQLite

Example values:
```
SECRET_KEY=your_secure_random_string_here
ADMIN_PASSWORD=your_secure_admin_password
PRODUCTION=True
```

### 4. Configure the Web App on PythonAnywhere

1. Go to the "Web" tab in PythonAnywhere
2. Click "Add a new web app"
3. Choose "Manual configuration" and select Python 3.9
4. Set the following configuration:
   - Source code: `/home/yourusername/QMS_aeon`
   - Working directory: `/home/yourusername/QMS_aeon`
   - WSGI configuration file: Edit the WSGI file to point to the `wsgi.py` file in your project

### 5. Configure the WSGI File

Make sure your WSGI file points to the application:

```python
import sys
import os

# Add the application directory to the Python path
path = '/home/yourusername/QMS_aeon'
if path not in sys.path:
    sys.path.append(path)

# Import the Flask application
from app import app as application

# PythonAnywhere uses WSGI to serve the application
```

### 6. Database Setup

The application will automatically create the SQLite database on first run. If you're using a different database, make sure to set the `DATABASE_URL` environment variable.

### 7. Static Files

Configure static files in the PythonAnywhere dashboard:
- URL: `/static/`
- Directory: `/home/yourusername/QMS_aeon/static/`

### 8. Reload the Web App

Click the "Reload" button in the PythonAnywhere dashboard to apply all changes.

## Maintenance and Updates

### Updating the Application

1. SSH into your PythonAnywhere account
2. Navigate to your project directory
3. Pull the latest changes:
   ```
   cd ~/QMS_aeon
   git pull origin production
   ```
4. Reload the web app from the PythonAnywhere dashboard

### Backup

Regularly backup your database file (if using SQLite) or set up automated backups for your database.

## Troubleshooting

- Check the error logs in the PythonAnywhere dashboard
- Ensure all required environment variables are set
- Verify that the virtual environment has all dependencies installed
- Make sure the WSGI file is correctly configured

## Security Considerations

- Keep your `SECRET_KEY` and `ADMIN_PASSWORD` secure
- Regularly update your admin password
- Consider implementing proper password hashing for employee accounts
- Set up HTTPS for your PythonAnywhere domain
