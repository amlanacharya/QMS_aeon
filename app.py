# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import pandas as pd
import io
import qrcode
import base64
import io
import urllib.parse


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tokens.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Custom context processor for current year
@app.context_processor
def inject_now():
    def now():
        return datetime.utcnow().strftime('%Y')
    return {'now': now}

db = SQLAlchemy(app)

# Token model
class Token(db.Model):
    __tablename__ = 'tokens'
    id = db.Column(db.Integer, primary_key=True)
    token_number = db.Column(db.String(10), nullable=False)
    application_number = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    customer_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='PENDING')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    printer_mac = db.Column(db.String(20), default='')

# System settings model
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    queue_active = db.Column(db.Boolean, default=True)
    current_token_id = db.Column(db.Integer, default=0)
    last_token_number = db.Column(db.Integer, default=0)

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    # Initialize settings if not present
    if not Settings.query.first():
        db.session.add(Settings(queue_active=True, current_token_id=0, last_token_number=0))
        db.session.commit()

# Helper functions
def generate_print_qr(content, device_address=None):
    """Generate a QR code for printing the content via the Bluetooth printing app"""
    # Create the content URI for your app
    # We're using "bluetoothprint://" as a custom scheme that would launch your app
    url = f"bluetoothprint://print?content={urllib.parse.quote(content)}"
    
    # Add device address if provided
    if device_address:
        url += f"&device_address={device_address}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create an image from the QR Code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the image to a bytes buffer
    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)
    
    # Convert to base64 for embedding in HTML
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"

def get_settings():
    return Settings.query.first()

def get_current_token():
    settings = get_settings()
    if settings.current_token_id == 0:
        return None
    return Token.query.get(settings.current_token_id)

def get_next_token():
    current_token = get_current_token()
    if not current_token:
        next_token = Token.query.filter_by(status='PENDING').order_by(Token.id).first()
    else:
        next_token = Token.query.filter(Token.id > current_token.id, Token.status == 'PENDING').order_by(Token.id).first()
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
    
    application_number = request.form.get('application_number')
    phone_number = request.form.get('phone_number')
    customer_name = request.form.get('customer_name')
    
    token_number = generate_token_number()
    
    new_token = Token(
        token_number=token_number,
        application_number=application_number,
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
            db.session.commit()
            
        settings.current_token_id = next_token.id
        db.session.commit()
    else:
        flash('No more pending tokens in queue', 'info')
    
    return redirect(url_for('index'))

@app.route('/recall-token')
def recall_token():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))
    
    # Just redirects back - the current token will be displayed again
    return redirect(url_for('index'))

@app.route('/skip-token')
def skip_token():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))
    
    current_token = get_current_token()
    if current_token:
        current_token.status = 'SKIPPED'
        db.session.commit()
        
    return redirect(url_for('next_token'))

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
    
    # In a real app, implement filtering by date, status, etc.
    tokens = Token.query.all()
    
    # Convert to DataFrame
    data = []
    for token in tokens:
        data.append({
            'Token Number': token.token_number,
            'Application Number': token.application_number,
            'Phone Number': token.phone_number,
            'Customer Name': token.customer_name,
            'Status': token.status,
            'Created At': token.created_at
        })
    
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
    
    application_number = request.form.get('application_number')
    phone_number = request.form.get('phone_number')
    customer_name = request.form.get('customer_name')
    
    token_number = generate_token_number()
    
    new_token = Token(
        token_number=token_number,
        application_number=application_number,
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
                        data.append({
                            'Token Number': token.token_number,
                            'Application Number': token.application_number,
                            'Phone Number': token.phone_number,
                            'Customer Name': token.customer_name,
                            'Status': token.status,
                            'Created At': token.created_at
                        })
                    
                    # Create a backup filename with timestamp
                    backup_time = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
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
@app.route('/print-qr/<int:token_id>')
def print_qr(token_id):
    """Generate a QR code for printing a specific token"""
    token = Token.query.get(token_id)
    if not token:
        flash('Token not found', 'error')
        return redirect(url_for('index'))
    
    # Format content for printing
    content = f"""Token: {token.token_number}
Name: {token.customer_name}
App No: {token.application_number}
Phone: {token.phone_number}
Time: {token.created_at.strftime('%Y-%m-%d %H:%M')}

Please wait for your number to be called
Thank you for your patience!"""
    
    # Get device address from configuration if available
    device_address = None
    
    # Generate QR code
    qr_code = generate_print_qr(content, device_address)
    
    # Pass the is_admin value to the template
    return render_template('print_qr.html', token=token, qr_code=qr_code, content=content, is_admin=is_admin())

@app.route('/printer-settings', methods=['GET', 'POST'])
def printer_settings():
    if not is_admin():
        flash('Admin access required', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        printer_mac = request.form.get('printer_mac')
        # Save the printer MAC address to settings
        settings = get_settings()
        # You'll need to add the printer_mac column to your Settings model
        if hasattr(settings, 'printer_mac'):
            settings.printer_mac = printer_mac
            db.session.commit()
            flash('Printer settings updated', 'success')
        else:
            flash('Printer settings not available', 'error')
    
    settings = get_settings()
    printer_mac = getattr(settings, 'printer_mac', '') if hasattr(settings, 'printer_mac') else ''
    
    return render_template('printer_settings.html', printer_mac=printer_mac)

if __name__ == '__main__':
    app.run(debug=True)