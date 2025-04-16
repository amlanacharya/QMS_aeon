# Gunicorn configuration file for QMS application

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
worker_class = "eventlet"  # Required for SocketIO
workers = 1  # For SocketIO, we need only one worker
threads = 4
timeout = 120

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/qms.pid"
umask = 0
user = "www-data"
group = "www-data"

# Logging
errorlog = "/var/log/gunicorn/qms-error.log"
accesslog = "/var/log/gunicorn/qms-access.log"
loglevel = "info"

# Process naming
proc_name = "qms"

# Server hooks
def on_starting(server):
    server.log.info("Starting QMS application")

def on_exit(server):
    server.log.info("Stopping QMS application")
