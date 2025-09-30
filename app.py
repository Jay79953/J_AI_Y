from flask import Flask, render_template, request, jsonify, send_file
import random
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)

# === Gmail Credentials ===
SENDER_EMAIL = "builderofai80@gmail.com"
SENDER_PASS = "xjrd wlzn biez bgjl"  # Use App Passwords

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Check if using environment variable or local file
creds_json = os.environ.get("GOOGLE_CREDS")
if creds_json:
    # Using environment variable (for production/Render)
    creds_dict = json.loads(creds_json)
    # Fix escaped newlines in private key
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    # Using local file (for development)
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

client = gspread.authorize(creds)
sheet = client.open("Users").sheet1

# === OTP Store === (Temporary dict for testing)
otp_store = {}

@app.route('/')
def index():
    return send_file("index.html")

@app.route('/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to user's email"""
    data = request.get_json()
    email = data.get("email")
    
    if not email:
        return jsonify({"status": "error", "message": "Email is required"})
    
    otp = str(random.randint(100000, 999999))
    otp_store[email] = otp

    try:
        msg = MIMEText(f"Your Askify OTP is: {otp}")
        msg['Subject'] = "Askify OTP"
        msg['From'] = SENDER_EMAIL
        msg['To'] = email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, [email], msg.as_string())
        server.quit()

        return jsonify({"status": "sent"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP entered by user"""
    data = request.get_json()
    email = data.get("email")
    otp_entered = data.get("otp")
    
    if not email or not otp_entered:
        return jsonify({"status": "error", "message": "Email and OTP are required"})
    
    real_otp = otp_store.get(email)

    if real_otp and otp_entered == real_otp:
        return jsonify({"status": "verified"})
    else:
        return jsonify({"status": "invalid"})

@app.route('/register', methods=['POST'])
def register():
    """Register new user - Returns JSON success instead of file"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ["email", "password", "bank_name", "upi", "method"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"status": "error", "message": f"{field} is required"})
    
    email = data["email"]
    password = data["password"]
    bank_name = data["bank_name"]
    upi = data["upi"]
    method = data["method"]
    device_id = data.get("device_id", "web")
    
    try:
        # Check if user already exists
        existing = sheet.get_all_records()
        for row in existing:
            if row.get("Gmail") == email:
                return jsonify({"status": "exists", "message": "Email already registered"})
        
        # Add user to spreadsheet
        sheet.append_row([email, password, bank_name, method, upi, device_id, 1, "0"])
        
        # Clear OTP from store after successful registration
        if email in otp_store:
            del otp_store[email]
        
        # Return success JSON instead of file
        return jsonify({"status": "success", "message": "Registration successful"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/download-file', methods=['GET'])
def download_file():
    """Handle file download separately from registration"""
    try:
        file_path = "ASKIFY.rar"
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({"status": "error", "message": "File not found"}), 404
            
        return send_file(
            file_path, 
            as_attachment=True, 
            download_name='ASKIFY.rar',
            mimetype='application/x-rar-compressed'
        )
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"})
    
    try:
        records = sheet.get_all_records()
        for row in records:
            if row.get("Gmail") == email and row.get("Password") == password:
                return jsonify({"status": "success", "message": "Login successful"})
        
        return jsonify({"status": "invalid", "message": "Invalid credentials"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Server is running"})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
