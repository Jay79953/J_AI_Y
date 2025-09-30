from flask import Flask, request, jsonify, send_file
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Check if using environment variable or local file
creds_json = os.environ.get("GOOGLE_CREDS")
if creds_json:
    # Using environment variable (for production/Render)
    creds_dict = json.loads(creds_json)
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    # Using local file (for development)
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

client = gspread.authorize(creds)
sheet = client.open("Users").sheet1


@app.route('/')
def index():
    return send_file("index.html")


@app.route('/register', methods=['POST'])
def register():
    """Register new user directly after signup → payment"""
    data = request.get_json()

    # Validate required fields
    required_fields = ["email", "password", "name", "upi", "method"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"status": "error", "message": f"{field} is required"})

    email = data["email"]
    password = data["password"]
    name = data["name"]  # maps to "Name" column
    upi = data["upi"]    # maps to "UPI" column
    method = data["method"]  # maps to "Method" column
    uuid = data.get("uuid", "web")  # maps to "UUID" column

    try:
        # Check if user already exists
        existing = sheet.get_all_records()
        for row in existing:
            if row.get("Gmail") == email:
                return jsonify({"status": "exists", "message": "Email already registered"})

        # Add user to spreadsheet in correct order
        sheet.append_row([email, password, name, method, upi, uuid, 1, "0"])

        return jsonify({"status": "success", "message": "Registration successful"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/download-file', methods=['GET'])
def download_file():
    """Handle file download after registration"""
    try:
        file_path = "ASKIFY.rar"

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
