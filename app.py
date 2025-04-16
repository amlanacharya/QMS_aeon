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
    
    # Current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    obj8 = {"type": 0, "content": current_time, "bold": 0, "align": 1, "format": 0}
    a.append(obj8)
    
    # Convert list to dict with numerical keys as the app requires
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