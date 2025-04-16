# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone, timedelta
import os
import pandas as pd
import io
import json

app = Flask(__name__)

# Use environment variable for SECRET_KEY if available, otherwise use a secure default
# In production, set this environment variable to a secure random value
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a8c7ef9d2b4e6f8a0c2e4d6b8a0c2e4d6b8a0c2e4d6b8a0c2e4d6b')

# Configure database URI - use environment variable if available
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tokens.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure production settings
app.config['PRODUCTION'] = os.environ.get('PRODUCTION', 'False').lower() == 'true'

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

# Function to get current time in IST
def get_ist_time():
    return datetime.now(timezone.utc).astimezone(IST)

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send current token and queue status to the newly connected client
    current_token = get_current_token()
    next_token = get_next_token()
    settings = get_settings()

    # Get recently skipped tokens
    skipped_tokens = Token.query.filter_by(status='SKIPPED').order_by(Token.last_skipped_at.desc()).limit(10).all()

    # Convert token objects to dictionaries for JSON serialization
    current_token_data = None
    if current_token:
        current_token_data = {
            'token_number': current_token.token_number,
            'customer_name': current_token.customer_name,
            'visit_reason': current_token.visit_reason,
            'recall_count': current_token.recall_count
        }

    next_token_data = None
    if next_token:
        next_token_data = {
            'token_number': next_token.token_number
        }

    skipped_tokens_data = []
    for token in skipped_tokens:
        skipped_tokens_data.append({
            'token_number': token.token_number,
            'skipped_at': token.last_skipped_at.strftime('%H:%M:%S') if token.last_skipped_at else None
        })

    emit('queue_status', {
        'current_token': current_token_data,
        'next_token': next_token_data,
        'queue_active': settings.queue_active,
        'skipped_tokens': skipped_tokens_data
    })

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Helper function to broadcast token updates
def broadcast_token_update():
    current_token = get_current_token()
    next_token = get_next_token()
    settings = get_settings()

    # Get recently skipped tokens
    skipped_tokens = Token.query.filter_by(status='SKIPPED').order_by(Token.last_skipped_at.desc()).limit(10).all()

    # Convert token objects to dictionaries for JSON serialization
    current_token_data = None
    if current_token:
        current_token_data = {
            'token_number': current_token.token_number,
            'customer_name': current_token.customer_name,
            'visit_reason': current_token.visit_reason,
            'recall_count': current_token.recall_count
        }

    next_token_data = None
    if next_token:
        next_token_data = {
            'token_number': next_token.token_number
        }

    skipped_tokens_data = []
    for token in skipped_tokens:
        skipped_tokens_data.append({
            'token_number': token.token_number,
            'skipped_at': token.last_skipped_at.strftime('%H:%M:%S') if token.last_skipped_at else None
        })

    socketio.emit('queue_status', {
        'current_token': current_token_data,
        'next_token': next_token_data,
        'queue_active': settings.queue_active,
        'skipped_tokens': skipped_tokens_data
    })

# Custom context processors
@app.context_processor
def inject_now():
    def now():
        return get_ist_time().strftime('%Y')
    return {'now': now}

@app.context_processor
def inject_helpers():
    return {
        'get_active_reasons': get_active_reasons,
        'settings': get_settings()
    }

db = SQLAlchemy(app)

# Token model
class Token(db.Model):
    __tablename__ = 'tokens'
    id = db.Column(db.Integer, primary_key=True)
    token_number = db.Column(db.String(10), nullable=False)
    visit_reason = db.Column(db.String(50), nullable=False)  # Changed from application_number
    custom_reason = db.Column(db.String(100))  # New field for custom reason
    phone_number = db.Column(db.String(20))
    customer_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='PENDING')
    created_at = db.Column(db.DateTime, default=get_ist_time)
    # New fields for recall tracking
    recall_count = db.Column(db.Integer, default=0)
    last_recalled_at = db.Column(db.DateTime, nullable=True)
    # New fields for service time tracking
    served_at = db.Column(db.DateTime, nullable=True)
    service_duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    # New fields for enhanced analytics
    skip_count = db.Column(db.Integer, default=0)  # Track number of times skipped
    last_skipped_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)  # When service was completed
    resolution_outcome = db.Column(db.String(50), nullable=True)  # e.g., 'RESOLVED', 'REFERRED', etc.
    staff_id = db.Column(db.String(50), nullable=True)  # ID of staff who served the token
    complexity_level = db.Column(db.Integer, nullable=True)  # 1-5 rating of case complexity
    customer_feedback = db.Column(db.Integer, nullable=True)  # 1-5 rating from customer
    recovery_time = db.Column(db.Integer, nullable=True)
    previous_status = db.Column(db.String(20), nullable=True)


    @property
    def waiting_time(self):
        """Calculate waiting time in minutes from creation to being served, excluding time spent in SKIPPED state"""
        if not self.served_at:
            return None

        # Handle timezone-aware and naive datetime comparison
        if self.created_at.tzinfo is None and self.served_at.tzinfo is not None:
            # created_at is naive, served_at is aware
            served_at_naive = self.served_at.replace(tzinfo=None)
            delta = served_at_naive - self.created_at
        elif self.created_at.tzinfo is not None and self.served_at.tzinfo is None:
            # created_at is aware, served_at is naive
            created_at_naive = self.created_at.replace(tzinfo=None)
            delta = self.served_at - created_at_naive
        else:
            # Both are either naive or aware
            delta = self.served_at - self.created_at

        # Calculate total waiting time in seconds
        total_seconds = delta.total_seconds()

        # Subtract time spent in SKIPPED state if applicable
        if self.skip_count > 0 and self.recovery_time:
            # Subtract the recovery time (time between last skip and being served)
            total_seconds -= self.recovery_time

        # Ensure we don't return negative values
        return max(0, int(total_seconds / 60))

    @property
    def total_service_time(self):
        """Calculate total time from creation to completion in minutes"""
        if not self.completed_at:
            return None

        # Handle timezone-aware and naive datetime comparison
        if self.created_at.tzinfo is None and self.completed_at.tzinfo is not None:
            # created_at is naive, completed_at is aware
            completed_at_naive = self.completed_at.replace(tzinfo=None)
            delta = completed_at_naive - self.created_at
        elif self.created_at.tzinfo is not None and self.completed_at.tzinfo is None:
            # created_at is aware, completed_at is naive
            created_at_naive = self.created_at.replace(tzinfo=None)
            delta = self.completed_at - created_at_naive
        else:
            # Both are either naive or aware
            delta = self.completed_at - self.created_at

        return int(delta.total_seconds() / 60)

    @property
    def day_of_week(self):
        """Get the day of week when token was created"""
        return self.created_at.strftime('%A')

    @property
    def hour_of_day(self):
        """Get the hour of day when token was created"""
        return self.created_at.hour

# System settings model
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    queue_active = db.Column(db.Boolean, default=True)
    current_token_id = db.Column(db.Integer, default=0)
    last_token_number = db.Column(db.Integer, default=0)
    use_thermal_printer = db.Column(db.Boolean, default=True)  # True for thermal printer, False for standard printer

# Visit reason model
class Reason(db.Model):
    __tablename__ = 'reasons'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)  # e.g., 'reason1'
    description = db.Column(db.String(100), nullable=False)  # e.g., 'Reason 1'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    updated_at = db.Column(db.DateTime, default=get_ist_time, onupdate=get_ist_time)

# Employee model for tracking who serves which token
class Employee(db.Model):
    __tablename__ = 'employee'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), nullable=False, unique=True)  # Employee ID or username
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))  # e.g., 'admin', 'operator', etc.
    password = db.Column(db.String(100), nullable=False)  # Stores hashed password
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    last_login = db.Column(db.DateTime, nullable=True)
    is_on_duty = db.Column(db.Boolean, default=False)  # Whether employee is currently on duty

    # Method to set the password (hashes it)
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Method to check the password
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    # Statistics
    tokens_served = db.Column(db.Integer, default=0)
    avg_service_time = db.Column(db.Float, default=0.0)  # in minutes

# Token status change history model
class TokenStatusChange(db.Model):
    __tablename__ = 'token_status_changes'
    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, nullable=False)
    old_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime, default=get_ist_time)
    changed_by = db.Column(db.String(50), nullable=True)  # Employee ID who made the change

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    # Initialize settings if not present
    if not Settings.query.first():
        db.session.add(Settings(queue_active=True, current_token_id=0, last_token_number=0, use_thermal_printer=True))
        db.session.commit()

    # Initialize default reasons if not present
    if not Reason.query.first():
        default_reasons = [
            Reason(code='reason1', description='Reason 1'),
            Reason(code='reason2', description='Reason 2'),
            Reason(code='reason3', description='Reason 3'),
            Reason(code='reason4', description='Reason 4'),
            Reason(code='reason5', description='Reason 5'),
            Reason(code='reason6', description='Reason 6'),
        ]
        db.session.add_all(default_reasons)
        db.session.commit()

# Helper functions
def get_settings():
    return Settings.query.first()

def get_active_reasons():
    return Reason.query.filter_by(is_active=True).order_by(Reason.code).all()

def get_current_token():
    settings = get_settings()
    if settings.current_token_id == 0:
        return None
    return Token.query.get(settings.current_token_id)

def get_next_token():
    current_token = get_current_token()
    if not current_token:
        # If there's no current token, return the first pending token
        next_token = Token.query.filter_by(status='PENDING').order_by(Token.id).first()
    else:
        # First try to get the next token with a higher ID
        next_token = Token.query.filter(Token.id > current_token.id, Token.status == 'PENDING').order_by(Token.id).first()

        # If there's no pending token with a higher ID (e.g., when serving the last token first),
        # get the first pending token with a lower ID
        if not next_token:
            next_token = Token.query.filter(Token.id < current_token.id, Token.status == 'PENDING').order_by(Token.id).first()

    return next_token

def generate_token_number():
    settings = get_settings()
    new_token_number = settings.last_token_number + 1
    settings.last_token_number = new_token_number
    db.session.commit()
    return f"T{new_token_number:03d}"

# Authentication middleware
def is_admin():
    # Check if user is explicitly marked as admin
    if session.get('is_admin', False):
        return True

    # Check if user is an employee with admin role
    if 'employee_id' in session and 'employee_role' in session:
        if session['employee_role'] == 'admin':
            return True

    return False

# Routes
@app.route('/')
def index():
    settings = get_settings()
    current_token = get_current_token()
    next_token = get_next_token()
    skipped_tokens = Token.query.filter_by(status='SKIPPED').order_by(Token.last_skipped_at.desc()).limit(10).all()

    return render_template('index.html',
                          settings=settings,
                          current_token=current_token,
                          next_token=next_token,
                          skipped_tokens=skipped_tokens)

@app.route('/generate-token', methods=['POST'])
def generate_token():
    settings = get_settings()
    if not settings.queue_active:
        flash('Queue is currently paused. Cannot generate new tokens.', 'error')
        return redirect(url_for('index'))

    visit_reason = request.form.get('visit_reason')
    custom_reason = request.form.get('custom_reason')
    phone_number = request.form.get('phone_number')
    customer_name = request.form.get('customer_name')

    # Combine reason if it's "other"
    final_reason = f"Other: {custom_reason}" if visit_reason == 'other' else visit_reason

    token_number = generate_token_number()

    new_token = Token(
        token_number=token_number,
        visit_reason=final_reason,
        phone_number=phone_number,
        customer_name=customer_name
    )

    db.session.add(new_token)
    db.session.commit()

    flash(f'Token {token_number} generated successfully!', 'success')
    return redirect(url_for('token_confirmation', token_id=new_token.id))

@app.route('/token-confirmation/<int:token_id>')
def token_confirmation(token_id):
    token = Token.query.get(token_id)
    if not token:
        flash('Token not found', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    return render_template('token_confirmation.html', token=token, settings=settings)

@app.route('/next-token')
def next_token():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    next_token = get_next_token()
    if next_token:
        settings = get_settings()
        current_token = get_current_token()
        if current_token:
            current_token.status = 'SERVED'
            current_token.served_at = get_ist_time()
            # Calculate service duration in seconds
            if current_token.created_at:
                # Make sure both datetimes are comparable (either both naive or both aware)
                # If created_at is naive (no timezone info), make served_at naive too
                if current_token.created_at.tzinfo is None:
                    served_at_naive = current_token.served_at.replace(tzinfo=None)
                    delta = served_at_naive - current_token.created_at
                else:
                    # Both have timezone info
                    delta = current_token.served_at - current_token.created_at

                current_token.service_duration = int(delta.total_seconds())
            db.session.commit()

        settings.current_token_id = next_token.id
        db.session.commit()

        # Broadcast token update to all connected clients
        broadcast_token_update()
    else:
        flash('No more pending tokens in queue', 'info')

    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

@app.route('/recall-token')
def recall_token():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    current_token = get_current_token()
    if current_token:
        # Add recall count to track number of recalls
        if not hasattr(current_token, 'recall_count'):
            current_token.recall_count = 0
        current_token.recall_count += 1

        # Add last recall time
        current_token.last_recalled_at = get_ist_time()

        db.session.commit()

        # Broadcast token update to all connected clients
        broadcast_token_update()

        # Flash message with recall count
        flash(f'Recalling token {current_token.token_number} (Recall #{current_token.recall_count})', 'warning')
    else:
        flash('No active token to recall', 'error')

    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))



@app.route('/mark-as-served')
def mark_as_served():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    current_token = get_current_token()
    if current_token:
        # Mark the current token as SERVED
        current_token.status = 'SERVED'
        current_token.served_at = get_ist_time()

        # Record which employee served this token
        if 'employee_id' in session:
            employee_id = session['employee_id']
            current_token.staff_id = str(employee_id)

            # Update employee statistics
            employee = Employee.query.get(employee_id)
            if employee:
                employee.tokens_served += 1

                # Update average service time
                if current_token.created_at:
                    # Calculate service duration in seconds
                    if current_token.created_at.tzinfo is None:
                        served_at_naive = current_token.served_at.replace(tzinfo=None)
                        delta = served_at_naive - current_token.created_at
                    else:
                        delta = current_token.served_at - current_token.created_at

                    current_token.service_duration = int(delta.total_seconds())

                    if employee.tokens_served == 1:
                        employee.avg_service_time = current_token.service_duration / 60  # Convert to minutes
                    else:
                        # Weighted average to smooth out the values
                        employee.avg_service_time = (employee.avg_service_time * (employee.tokens_served - 1) +
                                                 current_token.service_duration / 60) / employee.tokens_served

        # Clear the current token
        settings = get_settings()
        settings.current_token_id = 0
        db.session.commit()

        # Broadcast token update to all connected clients
        broadcast_token_update()

        flash(f'Token {current_token.token_number} has been marked as served', 'success')
    else:
        flash('No active token to mark as served', 'error')

    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

# Admin routes
@app.route('/admin')
def admin():
    if not is_admin():
        return render_template('admin_login.html')

    settings = get_settings()
    tokens = Token.query.order_by(Token.id.desc()).limit(20).all()
    pending_tokens = Token.query.filter_by(status='PENDING').order_by(Token.id).all()

    return render_template('admin.html',
                          settings=settings,
                          tokens=tokens,
                          pending_tokens=pending_tokens)

@app.route('/admin-login', methods=['POST'])
def admin_login():
    # Use environment variable for admin password if available
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')

    if request.form.get('password') == admin_password:
        session['is_admin'] = True
        flash('Admin access granted', 'success')
        return redirect(url_for('admin'))

    flash('Invalid password', 'error')
    return redirect(url_for('admin'))

@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('Logged out', 'info')
    return redirect(url_for('index'))

@app.route('/toggle-queue')
def toggle_queue():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    settings.queue_active = not settings.queue_active
    db.session.commit()

    # Broadcast queue status update to all connected clients
    broadcast_token_update()

    state = 'activated' if settings.queue_active else 'paused'
    flash(f'Queue {state} successfully', 'success')
    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

@app.route('/reset-counter')
def reset_counter():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    settings.last_token_number = 0
    db.session.commit()

    flash('Token counter reset to 0', 'success')
    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

@app.route('/toggle-print-mode')
def toggle_print_mode():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    settings.use_thermal_printer = not settings.use_thermal_printer
    db.session.commit()

    mode = 'Thermal Printer' if settings.use_thermal_printer else 'Standard Printer'
    flash(f'Print mode changed to {mode}', 'success')
    return redirect(url_for('admin'))

@app.route('/export-data')
def export_data():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    try:
        # Get all tokens
        all_tokens = Token.query.all()

        # Prepare token data for export
        token_data = []
        for token in all_tokens:
            token_item = {
                'Token Number': token.token_number,
                'Visit Reason': token.visit_reason,
                'Phone Number': token.phone_number,
                'Customer Name': token.customer_name,
                'Status': token.status,
                'Created At': token.created_at,
                'Recall Count': token.recall_count,
                'Skip Count': token.skip_count,
                'Was Skipped': token.skip_count > 0,
            }

            # Add skipped token specific data
            if token.skip_count > 0:
                token_item['Last Skipped At'] = token.last_skipped_at
                # Include recovery time if the token was skipped but later served
                if token.status == 'SERVED' and token.served_at and token.last_skipped_at:
                    # Calculate recovery time if not stored directly
                    if hasattr(token, 'recovery_time') and token.recovery_time:
                        token_item['Recovery Time (sec)'] = token.recovery_time
                    else:
                        # Calculate on the fly if not stored
                        if token.last_skipped_at.tzinfo is None and token.served_at.tzinfo is not None:
                            # last_skipped_at is naive, served_at is aware
                            served_at_naive = token.served_at.replace(tzinfo=None)
                            recovery_delta = served_at_naive - token.last_skipped_at
                        elif token.last_skipped_at.tzinfo is not None and token.served_at.tzinfo is None:
                            # last_skipped_at is aware, served_at is naive
                            last_skipped_at_naive = token.last_skipped_at.replace(tzinfo=None)
                            recovery_delta = token.served_at - last_skipped_at_naive
                        else:
                            # Both are either naive or aware
                            recovery_delta = token.served_at - token.last_skipped_at

                        token_item['Recovery Time (sec)'] = int(recovery_delta.total_seconds())
                        token_item['Recovery Time (min)'] = round(int(recovery_delta.total_seconds()) / 60, 1)

            # Add service time data if available
            if token.served_at:
                token_item['Served At'] = token.served_at
                token_item['Waiting Time (min)'] = token.waiting_time

                if token.service_duration is not None:
                    # Convert seconds to minutes for better readability
                    token_item['Service Duration (min)'] = round(token.service_duration / 60, 1)

            token_data.append(token_item)

        tokens_df = pd.DataFrame(token_data)

        # Determine export format (CSV or Excel)
        export_format = request.args.get('format', 'csv')

        if export_format == 'excel':
            output = io.BytesIO()

            served_tokens = [t for t in all_tokens if t.status == 'SERVED' and t.served_at is not None]
            skipped_tokens = [t for t in all_tokens if t.status == 'SKIPPED' or t.skip_count > 0]
            pending_tokens = [t for t in all_tokens if t.status == 'PENDING']

            # Get tokens that were skipped but later served (recovered tokens)
            skipped_then_served = [t for t in served_tokens if t.skip_count > 0]

            # Get all employees
            staff_members = Employee.query.all()

            # Basic counts
            total_tokens = len(all_tokens)
            total_served = len(served_tokens)
            total_skipped = len(skipped_tokens)
            total_pending = len(pending_tokens)
            total_recovered = len(skipped_then_served)

            # Calculate recovery rate
            recovery_rate = (total_recovered / total_skipped * 100) if total_skipped > 0 else 0

            # Calculate service metrics
            if total_served > 0:
                avg_waiting_time = sum(token.waiting_time or 0 for token in served_tokens) / total_served
                avg_service_duration = sum(token.service_duration or 0 for token in served_tokens) / total_served / 60
                total_recalls = sum(token.recall_count or 0 for token in all_tokens)
                total_skips = sum(token.skip_count or 0 for token in all_tokens)
            else:
                avg_waiting_time = 0
                avg_service_duration = 0
                total_recalls = 0
                total_skips = 0

            # Time-based analytics
            day_stats = {}
            hour_stats = {}

            for token in all_tokens:
                # Day of week stats
                day = token.day_of_week
                if day not in day_stats:
                    day_stats[day] = {'count': 0, 'served': 0, 'skipped': 0, 'recovered': 0}

                day_stats[day]['count'] += 1
                if token.status == 'SERVED':
                    day_stats[day]['served'] += 1
                    if token.skip_count > 0:
                        day_stats[day]['recovered'] += 1
                elif token.status == 'SKIPPED' or token.skip_count > 0:
                    day_stats[day]['skipped'] += 1

                # Hour of day stats
                hour = token.hour_of_day
                if hour not in hour_stats:
                    hour_stats[hour] = {'count': 0, 'served': 0, 'skipped': 0, 'recovered': 0}

                hour_stats[hour]['count'] += 1
                if token.status == 'SERVED':
                    hour_stats[hour]['served'] += 1
                    if token.skip_count > 0:
                        hour_stats[hour]['recovered'] += 1
                elif token.status == 'SKIPPED' or token.skip_count > 0:
                    hour_stats[hour]['skipped'] += 1

            # Reason analytics
            reason_stats = {}
            for token in all_tokens:
                reason = token.visit_reason
                if reason not in reason_stats:
                    reason_stats[reason] = {
                        'count': 0,
                        'served': 0,
                        'skipped': 0,
                        'pending': 0,
                        'recovered': 0,
                        'total_waiting_time': 0,
                        'total_service_duration': 0,
                        'total_recalls': 0,
                        'total_skips': 0
                    }

                reason_stats[reason]['count'] += 1
                reason_stats[reason]['total_recalls'] += token.recall_count or 0
                reason_stats[reason]['total_skips'] += token.skip_count or 0

                if token.status == 'SERVED':
                    reason_stats[reason]['served'] += 1
                    if token.skip_count > 0:
                        reason_stats[reason]['recovered'] += 1
                    reason_stats[reason]['total_waiting_time'] += token.waiting_time or 0
                    reason_stats[reason]['total_service_duration'] += token.service_duration or 0 if token.service_duration else 0
                elif token.status == 'SKIPPED' or token.skip_count > 0:
                    reason_stats[reason]['skipped'] += 1
                elif token.status == 'PENDING':
                    reason_stats[reason]['pending'] += 1

            # Calculate averages for each reason
            for reason, stats in reason_stats.items():
                if stats['served'] > 0:
                    stats['avg_waiting_time'] = stats['total_waiting_time'] / stats['served']
                    stats['avg_service_duration'] = stats['total_service_duration'] / stats['served'] / 60
                else:
                    stats['avg_waiting_time'] = 0
                    stats['avg_service_duration'] = 0

            # Create DataFrames for each analytics section

            # Summary Statistics
            summary_data = {
                'Metric': [
                    'Total Tokens', 'Tokens Served', 'Tokens Skipped', 'Tokens Pending',
                    'Average Waiting Time (min)', 'Average Service Duration (min)',
                    'Total Recalls', 'Total Skips', 'Skipped Tokens Recovered', 'Recovery Rate (%)'
                ],
                'Value': [
                    total_tokens, total_served, total_skipped, total_pending,
                    round(avg_waiting_time, 1), round(avg_service_duration, 1),
                    total_recalls, total_skips, total_recovered, round(recovery_rate, 1)
                ]
            }
            summary_df = pd.DataFrame(summary_data)

            # Day of Week Analysis
            day_data = []
            for day, stats in day_stats.items():
                efficiency = round((stats['served'] / stats['count'] * 100), 1) if stats['count'] > 0 else 0
                recovery_rate = round((stats['recovered'] / stats['skipped'] * 100), 1) if stats['skipped'] > 0 else 0
                day_data.append({
                    'Day': day,
                    'Total': stats['count'],
                    'Served': stats['served'],
                    'Skipped': stats['skipped'],
                    'Recovered': stats['recovered'],
                    'Efficiency (%)': efficiency,
                    'Recovery Rate (%)': recovery_rate
                })
            day_df = pd.DataFrame(day_data)

            # Hour of Day Analysis
            hour_data = []
            for hour, stats in hour_stats.items():
                efficiency = round((stats['served'] / stats['count'] * 100), 1) if stats['count'] > 0 else 0
                recovery_rate = round((stats['recovered'] / stats['skipped'] * 100), 1) if stats['skipped'] > 0 else 0
                hour_data.append({
                    'Hour': f"{hour}:00",
                    'Total': stats['count'],
                    'Served': stats['served'],
                    'Skipped': stats['skipped'],
                    'Recovered': stats['recovered'],
                    'Efficiency (%)': efficiency,
                    'Recovery Rate (%)': recovery_rate
                })
            hour_df = pd.DataFrame(hour_data)

            # Visit Reason Analysis
            reason_data = []
            for reason, stats in reason_stats.items():
                recovery_rate = round((stats['recovered'] / stats['skipped'] * 100), 1) if stats['skipped'] > 0 else 0
                reason_data.append({
                    'Visit Reason': reason,
                    'Total': stats['count'],
                    'Served': stats['served'],
                    'Skipped': stats['skipped'],
                    'Recovered': stats['recovered'],
                    'Pending': stats['pending'],
                    'Recalls': stats['total_recalls'],
                    'Skips': stats['total_skips'],
                    'Avg. Wait (min)': round(stats['avg_waiting_time'], 1),
                    'Avg. Service (min)': round(stats['avg_service_duration'], 1),
                    'Recovery Rate (%)': recovery_rate
                })
            reason_df = pd.DataFrame(reason_data)

            # Staff Performance
            staff_data = []
            for staff in staff_members:
                staff_data.append({
                    'Staff ID': staff.employee_id,
                    'Name': staff.name,
                    'Role': staff.role,
                    'Tokens Served': staff.tokens_served,
                    'Avg. Service Time (min)': round(staff.avg_service_time, 1),
                    'Status': 'On Duty' if staff.is_on_duty else 'Off Duty',
                    'Last Login': staff.last_login
                })
            staff_df = pd.DataFrame(staff_data)

            # Recovery Analysis - New sheet for recovered tokens
            recovery_data = []
            for token in skipped_then_served:
                # Calculate recovery time if not stored directly
                recovery_time = None
                if hasattr(token, 'recovery_time') and token.recovery_time:
                    recovery_time = token.recovery_time
                elif token.last_skipped_at and token.served_at:
                    # Calculate on the fly
                    if token.last_skipped_at.tzinfo is None and token.served_at.tzinfo is not None:
                        served_at_naive = token.served_at.replace(tzinfo=None)
                        recovery_delta = served_at_naive - token.last_skipped_at
                    elif token.last_skipped_at.tzinfo is not None and token.served_at.tzinfo is None:
                        last_skipped_at_naive = token.last_skipped_at.replace(tzinfo=None)
                        recovery_delta = token.served_at - last_skipped_at_naive
                    else:
                        recovery_delta = token.served_at - token.last_skipped_at
                    recovery_time = int(recovery_delta.total_seconds())

                recovery_data.append({
                    'Token Number': token.token_number,
                    'Customer Name': token.customer_name,
                    'Visit Reason': token.visit_reason,
                    'Created At': token.created_at,
                    'Times Skipped': token.skip_count,
                    'Last Skipped At': token.last_skipped_at,
                    'Served At': token.served_at,
                    'Recovery Time (sec)': recovery_time,
                    'Recovery Time (min)': round(recovery_time / 60, 1) if recovery_time else None,
                    'Total Wait Time (min)': token.waiting_time,
                    'Staff ID': token.staff_id
                })
            recovery_df = pd.DataFrame(recovery_data)

            # Write all DataFrames to Excel file
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                tokens_df.to_excel(writer, sheet_name='Tokens', index=False)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                day_df.to_excel(writer, sheet_name='Day Analysis', index=False)
                hour_df.to_excel(writer, sheet_name='Hour Analysis', index=False)
                reason_df.to_excel(writer, sheet_name='Reason Analysis', index=False)
                staff_df.to_excel(writer, sheet_name='Staff Performance', index=False)
                recovery_df.to_excel(writer, sheet_name='Recovery Analysis', index=False)

                # Format the Excel file
                workbook = writer.book

                # Add some formatting to make it look better
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })

                # Apply formatting to each worksheet
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    # Get the column names from the DataFrame
                    if sheet_name == 'Tokens':
                        columns = tokens_df.columns
                    elif sheet_name == 'Summary':
                        columns = summary_df.columns
                    elif sheet_name == 'Day Analysis':
                        columns = day_df.columns
                    elif sheet_name == 'Hour Analysis':
                        columns = hour_df.columns
                    elif sheet_name == 'Reason Analysis':
                        columns = reason_df.columns
                    elif sheet_name == 'Staff Performance':
                        columns = staff_df.columns
                    elif sheet_name == 'Recovery Analysis':
                        columns = recovery_df.columns
                    else:
                        continue

                    # Apply header formatting
                    for col_num, value in enumerate(columns):
                        worksheet.write(0, col_num, value, header_format)

                    # Set column width
                    worksheet.set_column(0, len(columns), 15)

            output.seek(0)
            return send_file(output,
                            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            download_name='qms_analytics_export.xlsx',
                            as_attachment=True)
        else:  # Default to CSV - just export token data
            output = io.StringIO()
            tokens_df.to_csv(output, index=False)
            output.seek(0)
            return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                            mimetype='text/csv',
                            download_name='tokens_export.csv',
                            as_attachment=True)
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'error')
        if is_admin():
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))

@app.route('/admin-generate-token', methods=['POST'])
def admin_generate_token():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    if not settings.queue_active:
        flash('Queue is currently paused. Cannot generate new tokens.', 'error')
        # Redirect based on user type
        if is_admin():
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))

    visit_reason = request.form.get('visit_reason')
    other_reason = request.form.get('other_reason')
    phone_number = request.form.get('phone_number')
    customer_name = request.form.get('customer_name')

    # Combine reason if "Others" is selected
    final_reason = f"{visit_reason}: {other_reason}" if visit_reason == "Others" else visit_reason

    token_number = generate_token_number()

    new_token = Token(
        token_number=token_number,
        visit_reason=final_reason,
        phone_number=phone_number,
        customer_name=customer_name
    )

    db.session.add(new_token)
    db.session.commit()

    flash(f'Token {token_number} generated successfully!', 'success')

    # Redirect directly to the print page instead of confirmation
    return redirect(url_for('admin_print_token', token_id=new_token.id))

@app.route('/admin-print-token/<int:token_id>')
def admin_print_token(token_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    token = Token.query.get(token_id)
    if not token:
        flash('Token not found', 'error')
        # Redirect based on user type
        if is_admin():
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))

    # Check settings to determine which template to use
    settings = get_settings()
    if settings.use_thermal_printer:
        return render_template('thermal_print_token.html', token=token)
    else:
        return render_template('admin_print_token_legacy.html', token=token)
@app.route('/print-token/<int:token_id>')
def print_token(token_id):
    token = Token.query.get(token_id)
    if not token:
        flash('Token not found', 'error')
        return redirect(url_for('index'))

    # Check settings to determine which template to use
    settings = get_settings()
    if settings.use_thermal_printer:
        return render_template('thermal_print_token.html', token=token)
    else:
        return render_template('token_print_legacy.html', token=token)
@app.route('/standard-print-token/<int:token_id>')
def standard_print_token(token_id):
    token = Token.query.get(token_id)
    if not token:
        flash('Token not found', 'error')
        return redirect(url_for('index'))

    # For users who specifically want the old format
    if is_admin():
        return render_template('admin_print_token_legacy.html', token=token)
    else:
        return render_template('token_print_legacy.html', token=token)
@app.route('/reset-database', methods=['GET', 'POST'])
def reset_database():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Check for confirmation password
        if request.form.get('confirm_password') == 'admin123':
            try:
                # Export data before deletion if requested
                if request.form.get('export_before_delete') == 'yes':
                    # Save a backup of the data
                    tokens = Token.query.all()
                    data = []
                    for token in tokens:
                        token_data = {
                            'Token Number': token.token_number,
                            'Visit Reason': token.visit_reason,
                            'Phone Number': token.phone_number,
                            'Customer Name': token.customer_name,
                            'Status': token.status,
                            'Created At': token.created_at,
                            'Recall Count': token.recall_count
                        }

                        # Add service time data if available
                        if token.served_at:
                            token_data['Served At'] = token.served_at
                            token_data['Waiting Time (min)'] = token.waiting_time

                            if token.service_duration is not None:
                                # Convert seconds to minutes for better readability
                                token_data['Service Duration (min)'] = round(token.service_duration / 60, 1)

                        data.append(token_data)

                    # Create a backup filename with timestamp
                    backup_time = get_ist_time().strftime('%Y%m%d_%H%M%S')
                    if not os.path.exists('backups'):
                        os.makedirs('backups')

                    backup_path = f'backups/tokens_backup_{backup_time}.csv'

                    # Save to CSV
                    pd.DataFrame(data).to_csv(backup_path, index=False)
                    flash(f'Data backup created at {backup_path}', 'success')

                # Delete all tokens
                Token.query.delete()

                # Reset counters if requested
                if request.form.get('reset_counter') == 'yes':
                    settings = get_settings()
                    settings.last_token_number = 0
                    settings.current_token_id = 0

                # Commit the changes
                db.session.commit()

                flash('Database has been reset successfully', 'success')
                return redirect(url_for('admin'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error resetting database: {str(e)}', 'error')
                return redirect(url_for('reset_database'))
        else:
            flash('Invalid confirmation password', 'error')

    # GET request - show the confirmation form
    return render_template('reset_database.html')

@app.route('/revert-token-status/<int:token_id>')
def revert_token_status(token_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    token = Token.query.get_or_404(token_id)

    # Store previous status for message
    previous_status = token.status

    # Get the current token before making any changes
    current_token = get_current_token()

    # Check if this token was created before the current token,This helps determine if it should be the next to be served
    is_earlier_token = current_token and token.id < current_token.id

    # Revert to PENDING
    token.status = 'PENDING'

    # If this was the current token, clear it and find the next token to serve
    settings = get_settings()
    if settings.current_token_id == token_id:
        settings.current_token_id = 0  # Set to 0 instead of None for consistency
        db.session.commit()

        # Find the next token to serve
        next_token = get_next_token()
        if next_token:
            settings.current_token_id = next_token.id
            db.session.commit()
    else:
        # If this token came before the current token and is now pending,
        # it should be the next token to be served
        if is_earlier_token:

            pass

        db.session.commit()

    # Broadcast token update to all connected clients
    broadcast_token_update()

    flash(f'Token {token.token_number} status reverted from {previous_status} to PENDING', 'success')
    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

@app.route('/edit-token/<int:token_id>', methods=['GET', 'POST'])
def edit_token(token_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    token = Token.query.get_or_404(token_id)

    if request.method == 'POST':
        token.customer_name = request.form.get('customer_name')
        token.phone_number = request.form.get('phone_number')

        visit_reason = request.form.get('visit_reason')
        custom_reason = request.form.get('custom_reason')

        # Handle visit reason
        if visit_reason == 'other':
            token.visit_reason = f"Other: {custom_reason}"
        else:
            token.visit_reason = visit_reason

        db.session.commit()
        flash(f'Token {token.token_number} details updated successfully', 'success')
        # Redirect based on user type
        if is_admin():
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))

    return render_template('edit_token.html', token=token)

@app.route('/delete-token/<int:token_id>')
def delete_token(token_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    token = Token.query.get_or_404(token_id)

    # Only allow deletion of pending tokens
    if token.status != 'PENDING':
        flash('Only pending tokens can be deleted', 'error')
        return redirect(url_for('admin'))

    # Store token number for message
    token_number = token.token_number

    # Check if this token is the next token that would be served
    next_token = get_next_token()
    is_next_token = next_token and next_token.id == token.id

    # Delete the token
    db.session.delete(token)
    db.session.commit()


    if is_next_token:
        # Get the new next token after deletion
        new_next_token = get_next_token()

        # If there's no current token but there is a new next token, make it the current token
        settings = get_settings()
        if settings.current_token_id == 0 and new_next_token:
            settings.current_token_id = new_next_token.id
            db.session.commit()

    # Broadcast token update to all connected clients
    broadcast_token_update()

    flash(f'Token {token_number} has been deleted', 'success')
    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

# Reason Management Routes
@app.route('/manage-reasons')
def manage_reasons():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    reasons = Reason.query.order_by(Reason.code).all()
    return render_template('manage_reasons.html', reasons=reasons)

@app.route('/add-reason', methods=['GET', 'POST'])
def add_reason():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        code = request.form.get('code')
        description = request.form.get('description')
        is_active = request.form.get('is_active') == 'on'

        # Check if code already exists
        existing_reason = Reason.query.filter_by(code=code).first()
        if existing_reason:
            flash(f'Reason code "{code}" already exists', 'error')
            return redirect(url_for('add_reason'))

        new_reason = Reason(code=code, description=description, is_active=is_active)
        db.session.add(new_reason)
        db.session.commit()

        flash(f'Reason "{description}" added successfully', 'success')
        return redirect(url_for('manage_reasons'))

    return render_template('add_reason.html')

@app.route('/edit-reason/<int:reason_id>', methods=['GET', 'POST'])
def edit_reason(reason_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    reason = Reason.query.get_or_404(reason_id)

    if request.method == 'POST':
        code = request.form.get('code')
        description = request.form.get('description')
        is_active = request.form.get('is_active') == 'on'

        # Check if code already exists and it's not this reason's code
        existing_reason = Reason.query.filter_by(code=code).first()
        if existing_reason and existing_reason.id != reason_id:
            flash(f'Reason code "{code}" already exists', 'error')
            return redirect(url_for('edit_reason', reason_id=reason_id))

        reason.code = code
        reason.description = description
        reason.is_active = is_active
        reason.updated_at = get_ist_time()
        db.session.commit()

        flash(f'Reason "{description}" updated successfully', 'success')
        return redirect(url_for('manage_reasons'))

    return render_template('edit_reason.html', reason=reason)

@app.route('/delete-reason/<int:reason_id>')
def delete_reason(reason_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    reason = Reason.query.get_or_404(reason_id)

    # Check if this reason is being used by any tokens
    tokens_using_reason = Token.query.filter(Token.visit_reason.like(f'{reason.code}%')).count()
    if tokens_using_reason > 0:
        flash(f'Cannot delete reason "{reason.description}" as it is used by {tokens_using_reason} tokens', 'error')
        return redirect(url_for('manage_reasons'))

    db.session.delete(reason)
    db.session.commit()

    flash(f'Reason "{reason.description}" deleted successfully', 'success')
    return redirect(url_for('manage_reasons'))

# Redirect legacy analytics route to enhanced analytics
@app.route('/service-analytics')
def service_analytics():
    return redirect(url_for('enhanced_analytics'))

#route for Enchanced Analytics
@app.route('/enhanced-analytics')
def enhanced_analytics():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    # Get all tokens
    all_tokens = Token.query.all()
    served_tokens = [t for t in all_tokens if t.status == 'SERVED' and t.served_at is not None]
    skipped_tokens = [t for t in all_tokens if t.status == 'SKIPPED' or t.skip_count > 0]
    pending_tokens = [t for t in all_tokens if t.status == 'PENDING']

    # Get all employees
    staff_members = Employee.query.all()

    # Basic counts
    total_tokens = len(all_tokens)
    total_served = len(served_tokens)
    total_skipped = len(skipped_tokens)
    total_pending = len(pending_tokens)
    # Get tokens that were skipped but later served
    skipped_then_served = []
    for token in served_tokens:
        if token.skip_count > 0:
            skipped_then_served.append(token)
    # Calculate recovery metrics
    total_recovered = len(skipped_then_served)
    recovery_rate = (total_recovered / total_skipped * 100) if total_skipped > 0 else 0
    # Calculate average recovery time
    avg_recovery_time = sum(token.recovery_time or 0 for token in skipped_then_served) / total_recovered if total_recovered > 0 else 0

    # Calculate service metrics
    if total_served > 0:
        # Use the waiting_time property which now handles timezone differences
        avg_waiting_time = sum(token.waiting_time or 0 for token in served_tokens) / total_served

        # For service_duration, we've already calculated and stored it as an integer
        avg_service_duration = sum(token.service_duration or 0 for token in served_tokens) / total_served / 60

        total_recalls = sum(token.recall_count or 0 for token in all_tokens)
        total_skips = sum(token.skip_count or 0 for token in all_tokens)
    else:
        avg_waiting_time = 0
        avg_service_duration = 0
        total_recalls = 0
        total_skips = 0

    # Time-based analytics
    day_stats = {}
    hour_stats = {}

    for token in all_tokens:
        # Day of week stats
        day = token.day_of_week
        if day not in day_stats:
            day_stats[day] = {'count': 0, 'served': 0, 'skipped': 0}

        day_stats[day]['count'] += 1
        if token.status == 'SERVED':
            day_stats[day]['served'] += 1
        elif token.status == 'SKIPPED' or token.skip_count > 0:
            day_stats[day]['skipped'] += 1

        # Hour of day stats
        hour = token.hour_of_day
        if hour not in hour_stats:
            hour_stats[hour] = {'count': 0, 'served': 0, 'skipped': 0}

        hour_stats[hour]['count'] += 1
        if token.status == 'SERVED':
            hour_stats[hour]['served'] += 1
        elif token.status == 'SKIPPED' or token.skip_count > 0:
            hour_stats[hour]['skipped'] += 1

    # Reason analytics with more details
    reason_stats = {}
    for token in all_tokens:
        reason = token.visit_reason
        if reason not in reason_stats:
            reason_stats[reason] = {
                'count': 0,
                'served': 0,
                'skipped': 0,
                'pending': 0,
                'total_waiting_time': 0,
                'total_service_duration': 0,
                'total_recalls': 0,
                'total_skips': 0
            }

        reason_stats[reason]['count'] += 1
        reason_stats[reason]['total_recalls'] += token.recall_count or 0
        reason_stats[reason]['total_skips'] += token.skip_count or 0

        if token.status == 'SERVED':
            reason_stats[reason]['served'] += 1
            reason_stats[reason]['total_waiting_time'] += token.waiting_time or 0
            reason_stats[reason]['total_service_duration'] += token.service_duration or 0 if token.service_duration else 0
        elif token.status == 'SKIPPED' or token.skip_count > 0:
            reason_stats[reason]['skipped'] += 1
        elif token.status == 'PENDING':
            reason_stats[reason]['pending'] += 1

    # Calculate averages for each reason
    for reason, stats in reason_stats.items():
        if stats['served'] > 0:
            stats['avg_waiting_time'] = stats['total_waiting_time'] / stats['served']
            stats['avg_service_duration'] = stats['total_service_duration'] / stats['served'] / 60
        else:
            stats['avg_waiting_time'] = 0
            stats['avg_service_duration'] = 0

    return render_template('enhanced_analytics.html',
                          total_tokens=total_tokens,
                          total_served=total_served,
                          total_skipped=total_skipped,
                          total_pending=total_pending,
                          avg_waiting_time=avg_waiting_time,
                          avg_service_duration=avg_service_duration,
                          total_recalls=total_recalls,
                          total_skips=total_skips,
                          day_stats=day_stats,
                          hour_stats=hour_stats,
                          reason_stats=reason_stats,
                          all_tokens=all_tokens,
                          staff_members=staff_members,
                          skipped_then_served=skipped_then_served,
                        total_recovered=total_recovered,
                        recovery_rate=recovery_rate,
                        avg_recovery_time=avg_recovery_time)

# Employee Management Routes
@app.route('/manage-employees')
def manage_employees():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    employees = Employee.query.all()
    active_employee_count = Employee.query.filter_by(is_active=True).count()

    return render_template('manage_employees.html',
                          employees=employees,
                          active_employee_count=active_employee_count)

@app.route('/add-employee', methods=['POST'])
def add_employee():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    employee_id = request.form.get('employee_id')
    name = request.form.get('name')
    role = request.form.get('role')
    password = request.form.get('password')
    is_active = 'is_active' in request.form

    # Check if employee_id already exists
    existing_employee = Employee.query.filter_by(employee_id=employee_id).first()
    if existing_employee:
        flash(f'Employee ID {employee_id} already exists', 'error')
        return redirect(url_for('manage_employees'))

    # Create new employee
    new_employee = Employee(
        employee_id=employee_id,
        name=name,
        role=role,
        is_active=is_active
    )
    # Set password (this will hash it)
    new_employee.set_password(password)

    db.session.add(new_employee)
    db.session.commit()

    flash(f'Employee {name} added successfully', 'success')
    return redirect(url_for('manage_employees'))

@app.route('/edit-employee/<int:employee_id>')
def edit_employee(employee_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    employee = Employee.query.get_or_404(employee_id)
    return render_template('edit_employee.html', employee=employee)

@app.route('/update-employee/<int:employee_id>', methods=['POST'])
def update_employee(employee_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    employee = Employee.query.get_or_404(employee_id)

    # Check if employee_id is being changed and if it already exists
    new_employee_id = request.form.get('employee_id')
    if new_employee_id != employee.employee_id:
        existing_employee = Employee.query.filter_by(employee_id=new_employee_id).first()
        if existing_employee:
            flash(f'Employee ID {new_employee_id} already exists', 'error')
            return redirect(url_for('edit_employee', employee_id=employee_id))

    # Update employee details
    employee.employee_id = new_employee_id
    employee.name = request.form.get('name')
    employee.role = request.form.get('role')
    employee.is_active = 'is_active' in request.form

    # Only update password if provided
    password = request.form.get('password')
    if password and password.strip():
        employee.set_password(password)

    db.session.commit()

    flash(f'Employee {employee.name} updated successfully', 'success')
    return redirect(url_for('manage_employees'))

@app.route('/toggle-employee-status/<int:employee_id>')
def toggle_employee_status(employee_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    employee = Employee.query.get_or_404(employee_id)
    employee.is_active = not employee.is_active
    db.session.commit()

    status = 'activated' if employee.is_active else 'deactivated'
    flash(f'Employee {employee.name} {status} successfully', 'success')
    return redirect(url_for('manage_employees'))

# Employee Login Routes
@app.route('/employee-login')
def employee_login():
    return render_template('employee_login.html')

@app.route('/employee-login-process', methods=['POST'])
def employee_login_process():
    employee_id = request.form.get('employee_id')
    password = request.form.get('password')

    employee = Employee.query.filter_by(employee_id=employee_id).first()

    if employee and employee.check_password(password) and employee.is_active:
        session['employee_id'] = employee.id
        session['employee_name'] = employee.name
        session['employee_role'] = employee.role

        # Update last login time
        employee.last_login = get_ist_time()
        db.session.commit()

        flash(f'Welcome, {employee.name}!', 'success')

        # If employee is admin, redirect to admin page
        if employee.role == 'admin':
            session['is_admin'] = True
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))
    else:
        flash('Invalid credentials or account is inactive', 'error')
        return redirect(url_for('employee_login'))

@app.route('/employee-logout')
def employee_logout():
    # Clear employee session
    session.pop('employee_id', None)
    session.pop('employee_name', None)
    session.pop('employee_role', None)
    session.pop('is_admin', None)

    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/employee-dashboard')
def employee_dashboard():
    if 'employee_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('employee_login'))

    employee_id = session['employee_id']
    employee = Employee.query.get(employee_id)

    if not employee:
        session.clear()
        flash('Employee account not found', 'error')
        return redirect(url_for('employee_login'))

    settings = get_settings()
    current_token = get_current_token()
    next_token = get_next_token()
    pending_tokens = Token.query.filter_by(status='PENDING').order_by(Token.id).all()

    # Get all tokens for filtering in the template
    all_tokens = Token.query.order_by(Token.id.desc()).limit(50).all()

    # Get tokens served by this employee
    served_tokens = Token.query.filter_by(staff_id=str(employee.id), status='SERVED').order_by(Token.served_at.desc()).limit(10).all()

    return render_template('employee_dashboard.html',
                          employee=employee,
                          settings=settings,
                          current_token=current_token,
                          next_token=next_token,
                          pending_tokens=pending_tokens,
                          served_tokens=served_tokens,
                          all_tokens=all_tokens)

@app.route('/start-duty')
def start_duty():
    if 'employee_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('employee_login'))

    employee_id = session['employee_id']
    employee = Employee.query.get(employee_id)

    # Set all other employees to not on duty
    Employee.query.filter(Employee.id != employee_id).update({Employee.is_on_duty: False})

    employee.is_on_duty = True
    db.session.commit()

    flash(f'{employee.name} is now on duty', 'success')
    return redirect(url_for('employee_dashboard'))

@app.route('/end-duty')
def end_duty():
    if 'employee_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('employee_login'))

    employee_id = session['employee_id']
    employee = Employee.query.get(employee_id)

    employee.is_on_duty = False
    db.session.commit()

    flash(f'{employee.name} is now off duty', 'info')
    return redirect(url_for('employee_dashboard'))

@app.route('/serve-token/<int:token_id>')
def serve_token(token_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    token = Token.query.get_or_404(token_id)

    # Only pending or skipped tokens can be served
    if token.status != 'PENDING' and token.status != 'SKIPPED':
        flash(f'Only pending or skipped tokens can be served. Token {token.token_number} is {token.status}', 'error')
        if is_admin():
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))

    # Special handling for previously skipped tokens
    recovery_time = None
    if token.status == 'SKIPPED':
        # Calculate recovery time (time between skipping and serving)
        if token.last_skipped_at:
            current_time = get_ist_time()

            # Handle timezone differences
            if token.last_skipped_at.tzinfo is None and current_time.tzinfo is not None:
                # last_skipped_at is naive, current_time is aware
                current_time_naive = current_time.replace(tzinfo=None)
                recovery_delta = current_time_naive - token.last_skipped_at
            elif token.last_skipped_at.tzinfo is not None and current_time.tzinfo is None:
                # last_skipped_at is aware, current_time is naive
                last_skipped_at_naive = token.last_skipped_at.replace(tzinfo=None)
                recovery_delta = current_time - last_skipped_at_naive
            else:
                # Both are either naive or aware
                recovery_delta = current_time - token.last_skipped_at

            recovery_time = int(recovery_delta.total_seconds())
            token.recovery_time = recovery_time

        status_change = TokenStatusChange(
             token_id=token.id,
             old_status='SKIPPED',
             new_status='SERVED',
             changed_by=session.get('employee_id')
         )
        db.session.add(status_change)

        flash(f'Serving previously skipped token {token.token_number}. Token was skipped {token.skip_count} times.', 'info')

    # If there's a current token, mark it as served
    settings = get_settings()
    current_token = get_current_token()
    if current_token:
        current_token.status = 'SERVED'
        current_token.served_at = get_ist_time()

        # Record which employee served this token
        if 'employee_id' in session:
            employee_id = session['employee_id']
            current_token.staff_id = str(employee_id)

            # Update employee statistics
            employee = Employee.query.get(employee_id)
            if employee:
                employee.tokens_served += 1

                # Update average service time
                if current_token.service_duration:
                    if employee.tokens_served == 1:
                        employee.avg_service_time = current_token.service_duration / 60  # Convert to minutes
                    else:
                        # Weighted average to smooth out the values
                        employee.avg_service_time = (employee.avg_service_time * (employee.tokens_served - 1) +
                                                 current_token.service_duration / 60) / employee.tokens_served

        # Calculate service duration in seconds
        if current_token.created_at:

            if current_token.created_at.tzinfo is None:
                served_at_naive = current_token.served_at.replace(tzinfo=None)
                delta = served_at_naive - current_token.created_at
            else:
                # Both have timezone info
                delta = current_token.served_at - current_token.created_at

            current_token.service_duration = int(delta.total_seconds())

        db.session.commit()

    # Set the selected token as current
    settings.current_token_id = token.id
    db.session.commit()

    # Broadcast token update to all connected clients
    broadcast_token_update()

    flash(f'Now serving token {token.token_number}', 'success')

    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

# User Guide Route - Only accessible to authenticated users
@app.route('/user-guide')
def user_guide():
    # Check if user is authenticated (either admin or employee)
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    # Read the markdown file
    try:
        with open('QMS_User_Guide.md', 'r') as file:
            content = file.read()

        # Convert markdown to HTML
        try:
            import markdown
            html_content = markdown.markdown(content, extensions=['tables', 'toc'])
        except ImportError:
            # If markdown module is not available, just use the raw content
            html_content = f'<pre>{content}</pre>'

        return render_template('user_guide.html', content=html_content)
    except Exception as e:
        flash(f'Error loading user guide: {str(e)}', 'error')
        if is_admin():
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))
@app.route('/skip-token')
def skip_token():
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    current_token = get_current_token()
    if current_token:
        # Mark the current token as SKIPPED
        current_token.status = 'SKIPPED'

        # Store the previous status in case we need to recover
        current_token.previous_status = 'PENDING' if not current_token.previous_status else current_token.status

        # Increment skip count and record skip time
        current_token.skip_count += 1
        current_token.last_skipped_at = get_ist_time()

        # Record which employee skipped this token
        if 'employee_id' in session:
            employee_id = session['employee_id']
            # We'll reuse the staff_id field to track who performed the action
            if not current_token.staff_id:  # Only set if not already set
                current_token.staff_id = str(employee_id)

        # Find the next token to serve
        next_token = get_next_token()

        # Clear the current token
        settings = get_settings()
        settings.current_token_id = 0
        db.session.commit()

        # If there's a next token available, set it as the current token
        if next_token:
            settings.current_token_id = next_token.id
            db.session.commit()

        # Broadcast token update to all connected clients
        broadcast_token_update()

        flash(f'Token {current_token.token_number} has been skipped', 'warning')
    else:
        flash('No active token to skip', 'error')

    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

@app.route('/recover-token/<int:token_id>')
def recover_token(token_id):
    if not is_admin() and 'employee_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    token = Token.query.get_or_404(token_id)

    # Only skipped tokens can be recovered
    if token.status != 'SKIPPED':
        flash(f'Only skipped tokens can be recovered. Token {token.token_number} is {token.status}', 'error')
        if is_admin():
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('employee_dashboard'))

    # Calculate recovery time (time between skipping and recovering)
    if token.last_skipped_at:
        current_time = get_ist_time()

        # Handle timezone differences
        if token.last_skipped_at.tzinfo is None and current_time.tzinfo is not None:
            # last_skipped_at is naive, current_time is aware
            current_time_naive = current_time.replace(tzinfo=None)
            recovery_delta = current_time_naive - token.last_skipped_at
        elif token.last_skipped_at.tzinfo is not None and current_time.tzinfo is None:
            # last_skipped_at is aware, current_time is naive
            last_skipped_at_naive = token.last_skipped_at.replace(tzinfo=None)
            recovery_delta = current_time - last_skipped_at_naive
        else:
            # Both are either naive or aware
            recovery_delta = current_time - token.last_skipped_at

        recovery_time = int(recovery_delta.total_seconds())
        token.recovery_time = recovery_time

    # Change status back to PENDING
    token.status = 'PENDING'
    db.session.commit()

    # Broadcast token update to all connected clients
    broadcast_token_update()

    flash(f'Token {token.token_number} has been recovered and is now back in the pending queue', 'success')

    # Redirect based on user type
    if is_admin():
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('employee_dashboard'))

@app.route('/api/print-token/<int:token_id>')
def print_token_json(token_id):
    token = Token.query.get_or_404(token_id)
    formatted_date = token.created_at.strftime('%Y-%m-%d %H:%M')

    # Create a simple dictionary using the same format as your working simple test
    print_data = {
        "0": {
            "type": 0,
            "content": "Token Receipt",
            "bold": 1,
            "align": 1
        },
        "1": {
            "type": 0,
            "content": token.token_number,
            "bold": 1,
            "align": 1,
            "format": 2
        },
        "2": {
            "type": 0,
            "content": "Name: " + token.customer_name,
            "bold": 0,
            "align": 0
        },
        "3": {
            "type": 0,
            "content": "Reason: " + token.visit_reason,
            "bold": 0,
            "align": 0
        },
        "4": {
            "type": 0,
            "content": "Time: " + formatted_date,
            "bold": 0,
            "align": 0
        }
    }

    # Use jsonify the same way as your working function
    return jsonify(print_data)

@app.route('/api/print-test-simple')
def print_test_simple():
    print_data = {
        "0": {
            "type": 0,
            "content": "Simple Test",
            "bold": 1,
            "align": 1
        }
    }
    return jsonify(print_data)

@app.route('/print-test')
def print_test():
    settings = get_settings()
    # Only show the print test page if thermal printing is enabled
    if not settings.use_thermal_printer:
        flash('Thermal printing is currently disabled by the administrator', 'warning')
        return redirect(url_for('index'))
    return render_template('print_test.html')

@app.route('/api/print-test')
def print_test_json():
    print_data = {}

    print_data["0"] = {
        "type": 0,
        "content": "Printer Test",
        "bold": 1,
        "align": 1,
        "format": 1
    }

    print_data["1"] = {
        "type": 0,
        "content": " ",
        "bold": 0,
        "align": 1
    }

    print_data["2"] = {
        "type": 0,
        "content": "Normal Text",
        "bold": 0,
        "align": 0,
        "format": 0
    }

    print_data["3"] = {
        "type": 0,
        "content": "Bold Text",
        "bold": 1,
        "align": 0,
        "format": 0
    }

    print_data["4"] = {
        "type": 0,
        "content": "Centered Text",
        "bold": 0,
        "align": 1,
        "format": 0
    }

    print_data["5"] = {
        "type": 0,
        "content": "Right Aligned",
        "bold": 0,
        "align": 2,
        "format": 0
    }

    print_data["6"] = {
        "type": 0,
        "content": "Double Height",
        "bold": 0,
        "align": 1,
        "format": 1
    }

    print_data["7"] = {
        "type": 0,
        "content": "Double Size",
        "bold": 0,
        "align": 1,
        "format": 2
    }

    print_data["8"] = {
        "type": 0,
        "content": "Double Width",
        "bold": 0,
        "align": 1,
        "format": 3
    }

    print_data["9"] = {
        "type": 0,
        "content": "Small Font",
        "bold": 0,
        "align": 1,
        "format": 4
    }

    print_data["10"] = {
        "type": 0,
        "content": "-------------------------",
        "bold": 0,
        "align": 1,
        "format": 0
    }

    current_time = get_ist_time().strftime('%Y-%m-%d %H:%M:%S')
    print_data["11"] = {
        "type": 0,
        "content": f"Printed: {current_time}",
        "bold": 0,
        "align": 1
    }

    print_data["12"] = {
        "type": 0,
        "content": "Printer test complete",
        "bold": 1,
        "align": 1,
        "format": 0
    }

    return jsonify(print_data)

@app.route('/thermal-print-help')
def thermal_print_help():
    settings = get_settings()
    # Only show the thermal print help page if thermal printing is enabled
    if not settings.use_thermal_printer:
        flash('Thermal printing is currently disabled by the administrator', 'warning')
        return redirect(url_for('index'))
    return render_template('thermal_print_help.html')
@app.route('/simple-print-test')
def simple_print_test():
    return render_template('simple_print_test.html')
@app.route('/api/print-token-static/<int:token_id>')
def print_token_static(token_id):
    print_data = {
        "0": {
            "type": 0,
            "content": "Token Receipt",
            "bold": 1,
            "align": 1
        },
        "1": {
            "type": 0,
            "content": "T123",  # Hardcoded token number
            "bold": 1,
            "align": 1
        },
        "2": {
            "type": 0,
            "content": "Name: John Doe",  # Hardcoded name
            "bold": 0,
            "align": 0
        }
    }
    return jsonify(print_data)
@app.route('/api/print-exact-test')#will link in simple print test
def print_exact_test():
    # This matches EXACTLY the PHP example from the instructions
    a = {
        "0": {
            "type": 0,
            "content": "My Title",
            "bold": 1,
            "align": 2,
            "format": 3
        },
        "1": {
            "type": 0,
            "content": " ",
            "bold": 0,
            "align": 0
        }
    }

    return jsonify(a)
if __name__ == '__main__':
    # Only use debug mode and unsafe werkzeug in development
    debug_mode = not app.config['PRODUCTION']

    if debug_mode:
        socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
    else:
        # Production mode - no debug, no unsafe werkzeug
        socketio.run(app, debug=False)
