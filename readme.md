# Queue Management System with Bluetooth Printing

A robust, scalable, and maintainable queue management system built with Flask, featuring Bluetooth POS printer integration for Android tablets.

## Features

- User-friendly queue ticket generation system
- Admin dashboard for queue management
- Bluetooth thermal printer integration
- Android tablet compatibility
- Token status management (pending, served, skipped)
- Data export to CSV or Excel
- Responsive design for all devices

## System Architecture

The application follows SOLID principles and clean architecture:

1. **Core Application Layer**
   - Flask web application
   - SQLite database for data persistence
   - RESTful API endpoints

2. **Printer Integration Layer**
   - ESC/POS printer protocol support
   - Bluetooth device discovery and management
   - Thermal receipt formatting

3. **UI Layer**
   - Responsive Bootstrap templates
   - JavaScript for dynamic interactions
   - Android WebView integration

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/amlanacharya/QMS_Aeon.git
   cd QMS_Aeon
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Access the application at http://localhost:5000

## Android Integration

For Android tablet deployment, the application provides two methods of printing:

1. **Server-side printing**: The Flask server communicates with Bluetooth printers connected to the server.

2. **Client-side printing (Android)**: For Android tablets, the application leverages the WebView's JavaScript interface to communicate directly with Bluetooth printers.

### Setting Up Android WebView App

1. Create an Android app with a WebView that loads this application
2. Implement the JavaScript interface for Bluetooth printing
3. Grant necessary Bluetooth permissions

Example Android interface implementation:

```java
public class BluetoothPrinterInterface {
    @JavascriptInterface
    public void printToken(String tokenId) {
        // Implement printing logic
    }
    
    @JavascriptInterface
    public void startScan() {
        // Implement Bluetooth scanning
    }
    
    // Additional methods as needed
}

// In your WebView setup
webView.addJavascriptInterface(new BluetoothPrinterInterface(), "AndroidBTPrinter");
```

## Database Schema

The application uses SQLite with the following schema:

1. **Tokens Table**
   - id (Primary Key)
   - token_number
   - application_number
   - phone_number
   - customer_name
   - status
   - created_at

2. **Settings Table**
   - id (Primary Key)
   - queue_active
   - current_token_id
   - last_token_number

3. **Printer Settings Table**
   - id (Primary Key)
   - key
   - value
   - created_at
   - updated_at

## File Structure

```
QMS_Aeon/
├── app.py                     # Main application file
├── requirements.txt           # Dependencies
├── printer_service.py         # ESC/POS printing service
├── bluetooth_manager.py       # Bluetooth device management
├── settings_service.py        # Application settings service
├── printer_api.py             # Printer API endpoints
├── static/
│   ├── css/
│   │   └── print.css          # Print styles
│   └── js/
│       └── android_bluetooth.js # Android integration
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Main page
│   ├── admin.html             # Admin dashboard
│   ├── printer_settings.html  # Printer configuration page
│   └── thermal_print_token.html # Thermal printer formatting
└── instance/
    └── tokens.db              # SQLite database
```


## License

This project is licensed under the MIT License - see the LICENSE file for details.