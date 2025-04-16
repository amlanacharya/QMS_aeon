# Linux Server Deployment Guide for QMS System

This guide provides instructions for deploying the QMS (Queue Management System) application on a Linux server using Nginx, Gunicorn, and Systemd.

## Prerequisites

- A Linux server (Ubuntu/Debian recommended)
- Python 3.8 or higher
- Nginx
- Git

## Deployment Steps

### 1. Install Required Packages

```bash
# Update package lists
sudo apt update

# Install required packages
sudo apt install -y python3 python3-venv python3-pip nginx
```

### 2. Create a User for the Application (Optional)

```bash
# Create a user for the application
sudo useradd -m -s /bin/bash qms_user

# Add the user to the www-data group
sudo usermod -a -G www-data qms_user
```

### 3. Clone the Repository

```bash
# Create directory for the application
sudo mkdir -p /opt/qms

# Set ownership
sudo chown qms_user:www-data /opt/qms

# Clone the repository
sudo -u qms_user git clone https://github.com/amlanacharya/QMS_aeon.git /opt/qms
cd /opt/qms
sudo -u qms_user git checkout production
```

### 4. Set Up a Virtual Environment

```bash
# Create and activate a virtual environment
sudo -u qms_user python3 -m venv /opt/qms/venv
sudo -u qms_user /opt/qms/venv/bin/pip install --upgrade pip

# Install dependencies
sudo -u qms_user /opt/qms/venv/bin/pip install -r /opt/qms/requirements.txt
```

### 5. Configure Environment Variables

Create a .env file to store environment variables:

```bash
sudo -u qms_user touch /opt/qms/.env
sudo -u qms_user chmod 600 /opt/qms/.env
```

Edit the .env file and add the following:

```
PRODUCTION=True
SECRET_KEY=your_secure_random_string_here
ADMIN_PASSWORD=your_secure_admin_password
```

Generate a secure random string for SECRET_KEY:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### 6. Migrate Existing Passwords

If you're upgrading from a previous version that used plaintext passwords, run the password migration script:

```bash
cd /opt/qms
sudo -u qms_user /opt/qms/venv/bin/python migrate_passwords.py
```

This script will convert all plaintext passwords to secure bcrypt hashes.

### 7. Choose a Deployment Method

There are several ways to deploy the QMS application. Choose the method that best fits your requirements:

#### Option 7.1: Deploy with Nginx + Gunicorn (Recommended for Production)

This option uses Nginx as a reverse proxy and Gunicorn as the WSGI server, which is ideal for production environments.

##### 7.1.1. Configure Gunicorn

Copy the gunicorn.conf.py file to the application directory:

```bash
sudo mkdir -p /etc/gunicorn
sudo cp /opt/qms/gunicorn.conf.py /etc/gunicorn/qms.conf
```

Create directories for Gunicorn logs and pid:

```bash
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/run/gunicorn
sudo chown -R www-data:www-data /var/log/gunicorn
sudo chown -R www-data:www-data /var/run/gunicorn
```

##### 7.1.2. Configure Systemd Service

Copy the systemd service file:

```bash
sudo cp /opt/qms/qms.service /etc/systemd/system/
```

Edit the service file if necessary to update paths or environment variables:

```bash
sudo nano /etc/systemd/system/qms.service
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable qms
sudo systemctl start qms
```

##### 7.1.3. Configure Nginx

Install Nginx if not already installed:

```bash
sudo apt install -y nginx
```

Copy the Nginx configuration file:

```bash
sudo cp /opt/qms/nginx-qms.conf /etc/nginx/sites-available/qms
```

Edit the configuration file to update your domain or IP address:

```bash
sudo nano /etc/nginx/sites-available/qms
```

Create a symbolic link to enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/qms /etc/nginx/sites-enabled/
```

Test the Nginx configuration:

```bash
sudo nginx -t
```

Restart Nginx:

```bash
sudo systemctl restart nginx
```

#### Option 7.2: Deploy with Flask's Built-in Server (Simple Setup)

This option uses Flask's built-in server with a systemd service. It's simpler but less robust than the Nginx+Gunicorn option.

##### 7.2.1. Create a Simple Systemd Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/qms.service
```

Add the following content:

```
[Unit]
Description=QMS Application Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/qms
Environment="PATH=/opt/qms/venv/bin"
Environment="PRODUCTION=True"
Environment="SECRET_KEY=change_this_to_a_secure_random_string"
Environment="ADMIN_PASSWORD=change_this_to_a_secure_admin_password"
ExecStart=/opt/qms/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable qms
sudo systemctl start qms
```

#### Option 7.3: Deploy with uWSGI (Alternative to Gunicorn)

If you prefer uWSGI over Gunicorn, follow these steps:

##### 7.3.1. Install uWSGI

```bash
sudo -u qms_user /opt/qms/venv/bin/pip install uwsgi
```

##### 7.3.2. Create a uWSGI Configuration File

```bash
sudo nano /opt/qms/uwsgi.ini
```

Add the following content:

```ini
[uwsgi]
module = wsgi:application

master = true
processes = 5

socket = /tmp/qms.sock
chmod-socket = 660
chown-socket = www-data:www-data

vacuum = true
die-on-term = true
```

##### 7.3.3. Create a Systemd Service for uWSGI

```bash
sudo nano /etc/systemd/system/qms.service
```

Add the following content:

```
[Unit]
Description=uWSGI instance to serve QMS
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/qms
Environment="PATH=/opt/qms/venv/bin"
Environment="PRODUCTION=True"
Environment="SECRET_KEY=change_this_to_a_secure_random_string"
Environment="ADMIN_PASSWORD=change_this_to_a_secure_admin_password"
ExecStart=/opt/qms/venv/bin/uwsgi --ini uwsgi.ini

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable qms
sudo systemctl start qms
```

Then configure Nginx as described in Option 7.1.3, but modify the configuration to use the uWSGI socket.

### 8. Set Up Firewall (if needed)

If you're using UFW (Uncomplicated Firewall):

```bash
sudo ufw allow 'Nginx Full'
sudo ufw reload
```

### 9. Set Up SSL/TLS with Let's Encrypt (Recommended)

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Obtain and install a certificate:

```bash
sudo certbot --nginx -d qms.yourdomain.com
```

Follow the prompts to complete the setup.

## Database Management

The application uses SQLite by default, which is stored in the instance directory. For production, you might want to consider:

1. Regular backups of the SQLite database:

```bash
# Create a backup directory
sudo mkdir -p /opt/qms/backups
sudo chown qms_user:www-data /opt/qms/backups

# Set up a daily backup cron job
echo "0 2 * * * qms_user cp /opt/qms/instance/tokens.db /opt/qms/backups/tokens_$(date +\%Y\%m\%d).db" | sudo tee -a /etc/crontab
```

2. Or migrate to a more robust database like PostgreSQL for higher traffic scenarios.

## Maintenance and Updates

### Updating the Application

```bash
# Navigate to the application directory
cd /opt/qms

# Pull the latest changes
sudo -u qms_user git pull origin production

# Install any new dependencies
sudo -u qms_user /opt/qms/venv/bin/pip install -r requirements.txt

# Restart the service
sudo systemctl restart qms
```

### Monitoring the Application

Check the status of the service:

```bash
sudo systemctl status qms
```

View application logs:

```bash
# Gunicorn logs
sudo tail -f /var/log/gunicorn/qms-error.log
sudo tail -f /var/log/gunicorn/qms-access.log

# Nginx logs
sudo tail -f /var/log/nginx/qms-error.log
sudo tail -f /var/log/nginx/qms-access.log

# System logs
sudo journalctl -u qms
```

## Troubleshooting

### Service Won't Start

Check the service status:

```bash
sudo systemctl status qms
```

Look for errors in the logs:

```bash
sudo journalctl -u qms
```

### Nginx Issues

Check Nginx configuration:

```bash
sudo nginx -t
```

Check Nginx status:

```bash
sudo systemctl status nginx
```

### Permission Issues

Ensure proper ownership and permissions:

```bash
sudo chown -R qms_user:www-data /opt/qms
sudo chmod -R 755 /opt/qms
sudo chmod 600 /opt/qms/.env
```

## Security Considerations

1. **Keep your SECRET_KEY and ADMIN_PASSWORD secure**
2. **Use HTTPS with a valid SSL certificate**
3. **Implement proper password hashing for employee accounts**
4. **Regularly update the system and dependencies**
5. **Consider implementing a firewall and fail2ban**
6. **Set up regular backups**

## Additional Resources

- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Flask Deployment Options](https://flask.palletsprojects.com/en/2.0.x/deploying/)
- [Let's Encrypt](https://letsencrypt.org/docs/)
