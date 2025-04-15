# Thermal Printer Test App

A simple Flask application to test thermal printing via the Bluetooth Print app. This standalone application can be used to verify that your thermal printer setup works correctly before integrating it with your main application.

## Features

- Test print patterns with various text styles
- Print sample token receipts
- Detailed setup guide for thermal printing
- Compatible with 58mm thermal printers
- Works with the Bluetooth Print Android app

## Installation

1. Clone this repository or download the files
2. Set up a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required packages:
   ```
   pip install flask
   ```
4. Run the application:
   ```
   python app.py
   ```

## Deploying to PythonAnywhere

1. Create a PythonAnywhere account if you don't have one
2. Upload these files to your PythonAnywhere account
3. Set up a web app using Flask
4. Configure the WSGI file to point to your app
5. Make sure your templates directory is correctly set up

## Usage

1. Access the application from your mobile device
2. Install the Bluetooth Print app from Google Play Store
3. Connect your thermal printer to your device via Bluetooth or USB
4. Enable "Browser Print" function in the Bluetooth Print app settings
5. Click on the print test buttons in the app to test your setup

## File Structure

```
thermal-print-test/
├── app.py              # Main Flask application
├── templates/
│   ├── index.html      # Home page
│   ├── print_test.html # Test print page
│   └── setup_guide.html # Setup instructions
└── README.md           # This file
```

## Bluetooth Print App

This application is designed to work with the "Bluetooth Print" app for Android, which supports printing to Bluetooth and USB thermal printers. You can download it from the Google Play Store.

## Customization

You can customize the test print and sample token patterns by modifying the JSON objects in the `print_test_json()` and `print_sample_token()` functions in `app.py`.

## License

MIT License