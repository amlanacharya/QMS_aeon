# Gunicorn config

# Socket
bind = "0.0.0.0:5000"
backlog = 2048

# Workers
worker_class = "eventlet"  # For SocketIO
workers = 1  # Single worker for SocketIO
threads = 4
timeout = 120

# Server
daemon = False
pidfile = "/var/run/gunicorn/qms.pid"
umask = 0
user = "www-data"
group = "www-data"

# Logging
errorlog = "/var/log/gunicorn/qms-error.log"
accesslog = "/var/log/gunicorn/qms-access.log"
loglevel = "info"

# Process
proc_name = "qms"

# Hooks
def on_starting(server):
    server.log.info("Starting QMS application")

def on_exit(server):
    server.log.info("Stopping QMS application")
