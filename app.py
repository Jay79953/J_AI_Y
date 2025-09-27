from flask import Flask, render_template, request, jsonify, send_file
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)

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


@app.route('/')
def index():
    return send_file("index.html")


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
        file_path = "Askify.rar"   # or "welcome.txt"
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
