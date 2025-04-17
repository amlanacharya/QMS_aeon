# Queue Management System (QMS)

A comprehensive web-based Queue Management System designed to streamline customer service operations by efficiently managing customer queues. This system provides real-time token tracking, employee management, and detailed analytics.

## Features

- **Token Generation**: Customers can generate tokens with specific visit reasons
- **Real-time Queue Updates**: Live display of current and next tokens using WebSockets
- **Multi-level User Access**:
  - Customer view for token generation and tracking
  - Employee dashboard for serving customers
  - Admin interface for complete system management
- **Token Management**:
  - Serve, recall, and skip tokens
  - Mark tokens as served
  - Revert token status
  - Direct token selection for service
- **Employee Management**:
  - Track employee performance
  - Monitor service times
  - Record which employee handled each token
- **Analytics and Reporting**:
  - Service time tracking
  - Token statistics
  - Employee performance metrics
  - Data export to Excel
- **System Management**:
  - Configure visit reasons
  - Reset token counter
  - Pause/resume queue
  - Database management

## Technologies Used

- **Backend**: Flask (Python web framework)
- **Database**: SQLAlchemy with SQLite
- **Real-time Updates**: Flask-SocketIO
- **Frontend**:
  - HTML, CSS, JavaScript
  - Bootstrap 5
  - Socket.IO client
- **Data Processing**: Pandas for analytics and data export
- **Documentation**: Markdown for user guide

## Installation and Setup

1. Clone the repository:
   ```
   git clone https://github.com/amlanacharya/QMS_aeon
   cd QMS_aeon
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Access the application in your web browser:
   ```
   http://localhost:5000
   ```

## Usage

### Customer Interface
- Generate tokens by selecting visit reason and providing contact information
- View current and next token being served in real-time
- Print token for reference

### Employee Interface
- Login with employee credentials
- Serve, recall, or skip tokens
- Generate tokens for walk-in customers
- View pending tokens and recently served tokens
- Access basic analytics

### Admin Interface
- Complete system management
- Configure visit reasons
- Manage employee accounts
- Access comprehensive analytics
- Export data for external analysis
- Reset database when needed

## Project Structure

- `app.py`: Main application file containing routes and database models
- `templates/`: HTML templates for the web interface
- `static/`: Static files (CSS, JavaScript, images)
- `instance/`: Contains the SQLite database
- `QMS_User_Guide.md`: Comprehensive user guide

## User Roles

### Customer
- Generate tokens
- Track token status

### Employee
- Serve customers
- Manage tokens
- Generate tokens for walk-ins
- Access basic analytics

### Administrator
- All employee capabilities
- System configuration
- Employee management
- Advanced analytics
- Database management

## Deployment

This application can be deployed on various platforms:

### Linux Server Deployment

For deploying on a Linux server with Nginx, Gunicorn, and Systemd:

1. See the detailed instructions in [LINUX_DEPLOYMENT.md](LINUX_DEPLOYMENT.md)
2. Use the provided configuration files:
   - `nginx-qms.conf`: Nginx server configuration
   - `qms.service`: Systemd service file
   - `gunicorn.conf.py`: Gunicorn configuration
   - `deploy.sh`: Deployment script

### General Deployment Considerations

1. Set a secure `SECRET_KEY` through environment variables
2. Configure the database URI for production if needed
3. Set `PRODUCTION=True` in environment variables
4. Use a production-ready web server (Gunicorn with Nginx recommended)
5. Set up SSL/TLS for secure connections

## License

This project is licensed under the terms of the license included in the repository.

## Acknowledgements

- Flask and its extensions for providing the web framework
- Bootstrap for the responsive UI components
- Socket.IO for real-time communication
