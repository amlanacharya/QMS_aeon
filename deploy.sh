#!/bin/bash
# QMS Deployment Script for Linux Servers

# Exit on error
set -e

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Configuration variables
APP_DIR="/opt/qms"
APP_USER="www-data"
APP_GROUP="www-data"
VENV_DIR="$APP_DIR/venv"
NGINX_AVAILABLE="/etc/nginx/sites-available/qms"
NGINX_ENABLED="/etc/nginx/sites-enabled/qms"
SYSTEMD_SERVICE="/etc/systemd/system/qms.service"
GUNICORN_CONF="/etc/gunicorn/qms.conf"
LOG_DIR="/var/log/gunicorn"
PID_DIR="/var/run/gunicorn"

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p $APP_DIR
mkdir -p $LOG_DIR
mkdir -p $PID_DIR
mkdir -p /etc/gunicorn

# Set proper permissions
echo "Setting permissions..."
chown -R $APP_USER:$APP_GROUP $APP_DIR
chown -R $APP_USER:$APP_GROUP $LOG_DIR
chown -R $APP_USER:$APP_GROUP $PID_DIR

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv $VENV_DIR
  $VENV_DIR/bin/pip install --upgrade pip
fi

# Install dependencies
echo "Installing dependencies..."
$VENV_DIR/bin/pip install -r $APP_DIR/requirements.txt

# Copy configuration files
echo "Copying configuration files..."
cp $APP_DIR/nginx-qms.conf $NGINX_AVAILABLE
cp $APP_DIR/qms.service $SYSTEMD_SERVICE
cp $APP_DIR/gunicorn.conf.py $GUNICORN_CONF

# Create symbolic link for Nginx if it doesn't exist
if [ ! -f "$NGINX_ENABLED" ]; then
  echo "Enabling Nginx site..."
  ln -s $NGINX_AVAILABLE $NGINX_ENABLED
fi

# Reload systemd, enable and start services
echo "Configuring services..."
systemctl daemon-reload
systemctl enable qms
systemctl restart qms
systemctl restart nginx

# Check if services are running
echo "Checking service status..."
systemctl status qms --no-pager
systemctl status nginx --no-pager

echo "Deployment completed successfully!"
echo "You can access the application at http://your-server-ip"
echo "Remember to set up SSL/TLS for production use."
