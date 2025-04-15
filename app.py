from flask import Flask, render_template, jsonify, url_for, request
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    """Home page with links to test printing options"""
    return render_template('index.html')

@app.route('/api/print-test')
def print_test_json():
    """API endpoint that returns test print data in JSON format for 58mm printer"""
    # Create array of objects for test printing
    a = []
    
    # Title
    obj1 = {"type": 0, "content": "58mm Printer Test", "bold": 1, "align": 1, "format": 1}
    a.append(obj1)
    
    # Empty line
    obj2 = {"type": 0, "content": " ", "bold": 0, "align": 0, "format": 0}
    a.append(obj2)
    
    # Text formatting examples
    obj3 = {"type": 0, "content": "Normal text", "bold": 0, "align": 0, "format": 0}
    a.append(obj3)
    
    obj4 = {"type": 0, "content": "Bold text", "bold": 1, "align": 0, "format": 0}
    a.append(obj4)
    
    obj5 = {"type": 0, "content": "Centered text", "bold": 0, "align": 1, "format": 0}
    a.append(obj5)
    
    obj6 = {"type": 0, "content": "Large text", "bold": 0, "align": 1, "format": 2}
    a.append(obj6)
    
    # Divider
    obj7 = {"type": 0, "content": "-------------------------", "bold": 0, "align": 1, "format": 0}
    a.append(obj7)
    
    # Barcode (smaller for 58mm paper)
    obj8 = {"type": 2, "value": "12345678", "width": 80, "height": 40, "align": 1}
    a.append(obj8)
    
    # QR code (smaller for 58mm paper)
    obj9 = {"type": 3, "value": "Test QR Code", "size": 25, "align": 1}
    a.append(obj9)
    
    # Current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    obj10 = {"type": 0, "content": current_time, "bold": 0, "align": 1, "format": 0}
    a.append(obj10)
    
    # Convert list to dict with numerical keys as the app requires
    result = {}
    for i, obj in enumerate(a):
        result[str(i)] = obj
    
    return jsonify(result)

@app.route('/api/print-sample-token')
def print_sample_token():
    """API endpoint that returns sample token print data in JSON format"""
    # Sample token data
    token_number = "T001"
    customer_name = "John Doe"
    visit_reason = "General Inquiry"
    phone_number = "123-456-7890"
    formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Create array for the JSON data
    a = []
    
    # Title - centered
    obj1 = {"type": 0, "content": "Token Receipt", "bold": 1, "align": 1, "format": 0}
    a.append(obj1)
    
    # Empty line
    obj2 = {"type": 0, "content": " ", "bold": 0, "align": 0, "format": 0}
    a.append(obj2)
    
    # Token number - large and centered
    obj3 = {"type": 0, "content": token_number, "bold": 1, "align": 1, "format": 2}
    a.append(obj3)
    
    # Empty line
    obj4 = {"type": 0, "content": " ", "bold": 0, "align": 0, "format": 0}
    a.append(obj4)
    
    # Customer details - left aligned for better readability on narrow paper
    obj5 = {"type": 0, "content": "Name: " + customer_name, "bold": 0, "align": 0, "format": 0}
    a.append(obj5)
    
    obj6 = {"type": 0, "content": "Reason: " + visit_reason, "bold": 0, "align": 0, "format": 0}
    a.append(obj6)
    
    obj7 = {"type": 0, "content": "Phone: " + phone_number, "bold": 0, "align": 0, "format": 0}
    a.append(obj7)
    
    obj8 = {"type": 0, "content": "Time: " + formatted_date, "bold": 0, "align": 0, "format": 0}
    a.append(obj8)
    
    # Divider
    obj9 = {"type": 0, "content": "-------------------------", "bold": 0, "align": 1, "format": 0}
    a.append(obj9)
    
    # Footer - centered
    obj10 = {"type": 0, "content": "Please wait for your", "bold": 0, "align": 1, "format": 0}
    a.append(obj10)
    
    obj11 = {"type": 0, "content": "number to be called", "bold": 0, "align": 1, "format": 0}
    a.append(obj11)
    
    # QR code - smaller size for 58mm paper
    obj12 = {"type": 3, "value": token_number, "size": 25, "align": 1}
    a.append(obj12)
    
    # Convert list to dict with numerical keys
    result = {}
    for i, obj in enumerate(a):
        result[str(i)] = obj
    
    return jsonify(result)

@app.route('/print-test')
def print_test_page():
    """Page with a button to test thermal printing"""
    return render_template('print_test.html')

@app.route('/setup-guide')
def setup_guide():
    """Help page for thermal printing setup"""
    return render_template('setup_guide.html')

if __name__ == '__main__':
    app.run(debug=True)