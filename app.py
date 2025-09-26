from flask import Flask, render_template, request, jsonify, send_file
import random
import json
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# === Gmail Credentials ===
SENDER_EMAIL = "builderofai80@gmail.com"
SENDER_PASS = "xjrd wlzn biez bgjl"  # Use App Passwords

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ Read service account JSON from environment variable GOOGLE_CREDS
creds_json = os.environ.get("GOOGLE_CREDS")
if not creds_json:
    raise ValueError("❌ GOOGLE_CREDS environment variable is missing!")

creds_dict = json.loads(creds_json)

# 🔹 Fix escaped newlines in private key
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Users").sheet1

# === OTP Store === (Temporary dict for testing)
otp_store = {}

@app.route('/')
def index():
    return send_file("index.html")

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get("email")
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
    data = request.get_json()
    email = data.get("email")
    otp_entered = data.get("otp")

    real_otp = otp_store.get(email)
    if real_otp and otp_entered == real_otp:
        return jsonify({"status": "verified"})
    else:
        return jsonify({"status": "invalid"})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data["email"]
    password = data["password"]
    bank_name = data["bank_name"]
    upi = data["upi"]
    method = data["method"]
    device_id = data.get("device_id", "web")  # placeholder

    try:
        existing = sheet.get_all_records()
        for row in existing:
            if row.get("Gmail") == email:
                return jsonify({"status": "exists"})

        sheet.append_row([email, password, bank_name, method, upi, device_id, 1, "0"])

        # === After successful signup, send your existing file ===
        file_path = "Askify.rar"   # or "welcome.txt" if that's your file
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data["email"]
    password = data["password"]

    records = sheet.get_all_records()
    for row in records:
        if row.get("Gmail") == email and row.get("Password") == password:
            return jsonify({"status": "success"})
    return jsonify({"status": "invalid"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render provides this
    app.run(host='0.0.0.0', port=port)
