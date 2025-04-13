# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime, timezone, timedelta
import os
import pandas as pd
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tokens.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

# Function to get current time in IST
def get_ist_time():
    return datetime.now(timezone.utc).astimezone(IST)

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send current token and queue status to the newly connected client
    current_token = get_current_token()
    next_token = get_next_token()
    settings = get_settings()

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

    emit('queue_status', {
        'current_token': current_token_data,
        'next_token': next_token_data,
        'queue_active': settings.queue_active
    })

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Helper function to broadcast token updates
def broadcast_token_update():
    current_token = get_current_token()
    next_token = get_next_token()
    settings = get_settings()

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

    socketio.emit('queue_status', {
        'current_token': current_token_data,
        'next_token': next_token_data,
        'queue_active': settings.queue_active
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
        'get_active_reasons': get_active_reasons
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

    @property
    def waiting_time(self):
        """Calculate waiting time in minutes from creation to being served"""
        if not self.served_at:
            return None
        delta = self.served_at - self.created_at
        return int(delta.total_seconds() / 60)

    @property
    def total_service_time(self):
        """Calculate total time from creation to completion in minutes"""
        if not self.completed_at:
            return None
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

# Visit reason model
class Reason(db.Model):
    __tablename__ = 'reasons'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)  # e.g., 'reason1'
    description = db.Column(db.String(100), nullable=False)  # e.g., 'Reason 1'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    updated_at = db.Column(db.DateTime, default=get_ist_time, onupdate=get_ist_time)

# Staff model for tracking who serves which token
class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(20), nullable=False, unique=True)  # Staff ID or username
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))  # e.g., 'admin', 'operator', etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    last_login = db.Column(db.DateTime, nullable=True)

    # Statistics
    tokens_served = db.Column(db.Integer, default=0)
    avg_service_time = db.Column(db.Float, default=0.0)  # in minutes

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    # Initialize settings if not present
    if not Settings.query.first():
        db.session.add(Settings(queue_active=True, current_token_id=0, last_token_number=0))
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
    return session.get('is_admin', False)

# Routes
@app.route('/')
def index():
    settings = get_settings()
    current_token = get_current_token()
    next_token = get_next_token()
    return render_template('index.html',
                          settings=settings,
                          current_token=current_token,
                          next_token=next_token)

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

    return render_template('token_confirmation.html', token=token)

@app.route('/next-token')
def next_token():
    if not is_admin():
        flash('Admin access required', 'error')
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
                delta = current_token.served_at - current_token.created_at
                current_token.service_duration = int(delta.total_seconds())
            db.session.commit()

        settings.current_token_id = next_token.id
        db.session.commit()

        # Broadcast token update to all connected clients
        broadcast_token_update()
    else:
        flash('No more pending tokens in queue', 'info')

    return redirect(url_for('admin'))

@app.route('/recall-token')
def recall_token():
    if not is_admin():
        flash('Admin access required', 'error')
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

    return redirect(url_for('admin'))

@app.route('/skip-token')
def skip_token():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    current_token = get_current_token()
    if current_token:
        # Mark the current token as SKIPPED
        current_token.status = 'SKIPPED'

        # Increment skip count and record skip time
        current_token.skip_count += 1
        current_token.last_skipped_at = get_ist_time()

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

    return redirect(url_for('admin'))

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
    # In a real app, use proper auth
    if request.form.get('password') == 'admin123':
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
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    settings.queue_active = not settings.queue_active
    db.session.commit()

    # Broadcast queue status update to all connected clients
    broadcast_token_update()

    state = 'activated' if settings.queue_active else 'paused'
    flash(f'Queue {state} successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/reset-counter')
def reset_counter():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    settings.last_token_number = 0
    db.session.commit()

    flash('Token counter reset to 0', 'success')
    return redirect(url_for('admin'))

@app.route('/export-data')
def export_data():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    # Get all tokens
    tokens = Token.query.all()

    # Convert to DataFrame with correct fields
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

    df = pd.DataFrame(data)

    # Determine export format (CSV or Excel)
    export_format = request.args.get('format', 'csv')

    if export_format == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Tokens', index=False)
        output.seek(0)
        return send_file(output,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        download_name='tokens_export.xlsx',
                        as_attachment=True)
    else:  # Default to CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                        mimetype='text/csv',
                        download_name='tokens_export.csv',
                        as_attachment=True)

# New admin token generation routes
# Update the admin_generate_token route in app.py

@app.route('/admin-generate-token', methods=['POST'])
def admin_generate_token():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    settings = get_settings()
    if not settings.queue_active:
        flash('Queue is currently paused. Cannot generate new tokens.', 'error')
        return redirect(url_for('admin'))

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
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    token = Token.query.get(token_id)
    if not token:
        flash('Token not found', 'error')
        return redirect(url_for('admin'))

    # By default, use the thermal template
    return render_template('thermal_print_token.html', token=token)
@app.route('/print-token/<int:token_id>')
def print_token(token_id):
    token = Token.query.get(token_id)
    if not token:
        flash('Token not found', 'error')
        return redirect(url_for('index'))

    # Use the thermal template by default
    return render_template('thermal_print_token.html', token=token)
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
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('admin'))

    token = Token.query.get_or_404(token_id)

    # Store previous status for message
    previous_status = token.status

    # Get the current token before making any changes
    current_token = get_current_token()

    # Check if this token was created before the current token
    # This helps determine if it should be the next to be served
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
            # We don't need to do anything special here because get_next_token()
            # will correctly identify this token as the next one to be served
            # since it has a lower ID than the current token
            pass

        db.session.commit()

    # Broadcast token update to all connected clients
    broadcast_token_update()

    flash(f'Token {token.token_number} status reverted from {previous_status} to PENDING', 'success')
    return redirect(url_for('admin'))

@app.route('/edit-token/<int:token_id>', methods=['GET', 'POST'])
def edit_token(token_id):
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('admin'))

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
        return redirect(url_for('admin'))

    return render_template('edit_token.html', token=token)

@app.route('/delete-token/<int:token_id>')
def delete_token(token_id):
    if not is_admin():
        flash('Admin access required', 'error')
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

    # If we deleted the next token that would be served, we need to update the display
    # to show the new next token
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
    return redirect(url_for('admin'))

@app.route('/serve-token/<int:token_id>')
def serve_token(token_id):
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    token = Token.query.get_or_404(token_id)

    # Only pending tokens can be served
    if token.status != 'PENDING':
        flash(f'Only pending tokens can be served. Token {token.token_number} is {token.status}', 'error')
        return redirect(url_for('admin'))

    # No need to check if token is out of order anymore
    # Our improved get_next_token() function handles all cases

    # If there's a current token, mark it as served
    settings = get_settings()
    current_token = get_current_token()
    if current_token:
        current_token.status = 'SERVED'
        current_token.served_at = get_ist_time()
        # Calculate service duration in seconds
        if current_token.created_at:
            delta = current_token.served_at - current_token.created_at
            current_token.service_duration = int(delta.total_seconds())
        db.session.commit()

    # Set the selected token as current
    settings.current_token_id = token.id
    db.session.commit()

    # We don't need to do anything special here anymore since we've updated
    # the get_next_token() function to handle all cases correctly

    # Broadcast token update to all connected clients
    broadcast_token_update()

    flash(f'Now serving token {token.token_number}', 'success')
    return redirect(url_for('admin'))

# Reason Management Routes
@app.route('/manage-reasons')
def manage_reasons():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    reasons = Reason.query.order_by(Reason.code).all()
    return render_template('manage_reasons.html', reasons=reasons)

@app.route('/add-reason', methods=['GET', 'POST'])
def add_reason():
    if not is_admin():
        flash('Admin access required', 'error')
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
    if not is_admin():
        flash('Admin access required', 'error')
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
    if not is_admin():
        flash('Admin access required', 'error')
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

# Redirect old analytics route to enhanced analytics
@app.route('/service-analytics')
def service_analytics():
    return redirect(url_for('enhanced_analytics'))

# Enhanced Analytics Route with AI-Ready Data
@app.route('/enhanced-analytics')
def enhanced_analytics():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))

    # Get all tokens
    all_tokens = Token.query.all()
    served_tokens = [t for t in all_tokens if t.status == 'SERVED' and t.served_at is not None]
    skipped_tokens = [t for t in all_tokens if t.status == 'SKIPPED' or t.skip_count > 0]
    pending_tokens = [t for t in all_tokens if t.status == 'PENDING']

    # Basic counts
    total_tokens = len(all_tokens)
    total_served = len(served_tokens)
    total_skipped = len(skipped_tokens)
    total_pending = len(pending_tokens)

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
                          all_tokens=all_tokens)

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
