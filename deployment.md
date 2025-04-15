# Deploying the Thermal Print Test App on PythonAnywhere

These step-by-step instructions will help you deploy the Thermal Print Test application on PythonAnywhere so you can test your thermal printing integration.

## 1. Create a PythonAnywhere Account

If you don't already have one, create a free account at [PythonAnywhere](https://www.pythonanywhere.com/).

## 2. Set Up Files

Once logged in to PythonAnywhere:

1. Go to the "Files" tab
2. Create a new directory for your project:
   - Click "New directory"
   - Name it something like "thermal-print-test"
   - Navigate into that directory

3. Upload the files:
   - app.py
   - README.md

4. Create the templates directory:
   - Click "New directory" inside your project folder
   - Name it "templates"
   - Navigate into the templates directory

5. Upload the template files:
   - index.html
   - print_test.html
   - setup_guide.html

## 3. Create a Web App

1. Go to the "Web" tab
2. Click "Add a new web app"
3. Click "Next" on the first page
4. Select "Flask" as your web framework
5. Choose the latest Python version (3.9 or newer)
6. Set your project path:
   - Typically `/home/yourusername/thermal-print-test/`
7. Confirm your Flask application file:
   - It should be set to `/home/yourusername/thermal-print-test/app.py`
8. Complete the setup process

## 4. Configure the WSGI File

1. On the "Web" tab, click the link to edit your WSGI configuration file
2. Modify the Flask section to look something like this:

```python
import sys
path = '/home/yourusername/thermal-print-test'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
```

3. Make sure to replace `yourusername` with your actual PythonAnywhere username
4. Save the file

## 5. Reload the Web App

1. Go back to the "Web" tab
2. Click the green "Reload" button for your web app

## 6. Test Your Deployment

1. Visit your PythonAnywhere URL:
   - Usually `https://yourusername.pythonanywhere.com`
2. You should see the Thermal Printer Test App homepage
3. Access it from your Android device with the Bluetooth Print app installed
4. Follow the setup instructions on the page
5. Test printing using the provided buttons

## 7. Troubleshooting

If your app doesn't load correctly:

1. Check the error log on the "Web" tab
2. Make sure all files are in the correct directories
3. Verify your WSGI configuration
4. Ensure permissions are set correctly for all files
5. Check if the Flask app is properly set up in app.py

## 8. Thermal Printing Testing

1. On your Android device, install the Bluetooth Print app
2. Connect your thermal printer via Bluetooth or USB
3. Enable "