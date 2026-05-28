from flask import Flask, render_template, request, jsonify
import os, smtplib, threading, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_OK = True
except ImportError:
    GSPREAD_OK = False

app = Flask(__name__)

MAPBOX_TOKEN        = os.environ.get("MAPBOX_TOKEN", "")
NOTIFY_EMAIL        = os.environ.get("NOTIFY_EMAIL", "sam@thebizkeeper.com")
GMAIL_USER          = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD  = os.environ.get("GMAIL_APP_PASSWORD", "")
SHEETS_ID           = os.environ.get("GOOGLE_SHEETS_ID", "")
SERVICE_ACCOUNT_JSON= os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

def send_email(data):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("Email not configured — skipping")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"New Roof Lead — {data.get('name','Unknown')} | {data.get('address','')}"
        msg["From"]    = GMAIL_USER
        msg["To"]      = NOTIFY_EMAIL
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
          <div style="background:#0f172a;padding:20px 28px;border-radius:10px 10px 0 0">
            <h2 style="color:#10b981;margin:0">🏠 New RoofScan Pro Lead</h2>
          </div>
          <div style="border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
            <table style="width:100%;border-collapse:collapse">
              <tr><td style="padding:8px 0;color:#64748b;width:120px">Name</td><td style="font-weight:600">{data.get('name','')}</td></tr>
              <tr><td style="padding:8px 0;color:#64748b">Email</td><td>{data.get('email','')}</td></tr>
              <tr><td style="padding:8px 0;color:#64748b">Phone</td><td style="font-weight:600">{data.get('phone','')}</td></tr>
              <tr><td style="padding:8px 0;color:#64748b">Address</td><td>{data.get('address','')}</td></tr>
              <tr><td style="padding:8px 0;color:#64748b">Roof Size</td><td style="font-weight:600;color:#1a56db">{data.get('sqft','')} sq ft</td></tr>
              <tr><td style="padding:8px 0;color:#64748b">Material</td><td>{data.get('material','')}</td></tr>
              <tr><td style="padding:8px 0;color:#64748b">Ownership</td><td>{data.get('ownership','')}</td></tr>
              <tr><td style="padding:8px 0;color:#64748b">Submitted</td><td>{datetime.now().strftime('%b %d, %Y %I:%M %p')}</td></tr>
            </table>
          </div>
        </div>
        """
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
        print("Email sent OK")
    except Exception as e:
        print(f"Email error: {e}")

def save_to_sheets(data):
    if not GSPREAD_OK or not SERVICE_ACCOUNT_JSON or not SHEETS_ID:
        print("Sheets not configured — skipping")
        return
    try:
        creds = Credentials.from_service_account_info(
            json.loads(SERVICE_ACCOUNT_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        ws = gspread.authorize(creds).open_by_key(SHEETS_ID).sheet1
        if not ws.get_all_values():
            ws.append_row(["Name","Email","Phone","Address","Sq Ft","Material","Ownership","Submitted"])
        ws.append_row([
            data.get("name",""),
            data.get("email",""),
            data.get("phone",""),
            data.get("address",""),
            data.get("sqft",""),
            data.get("material",""),
            data.get("ownership",""),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ])
        print("Saved to Sheets OK")
    except Exception as e:
        print(f"Sheets error: {e}")

@app.route("/")
def index():
    return render_template("index.html", mapbox_token=MAPBOX_TOKEN)

@app.route("/api/lead", methods=["POST"])
def save_lead():
    data = request.get_json() or {}
    print("=== NEW ROOF LEAD ===")
    for k, v in data.items():
        print(f"  {k}: {v}")
    threading.Thread(target=send_email,    args=(data,), daemon=True).start()
    threading.Thread(target=save_to_sheets, args=(data,), daemon=True).start()
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5300))
    app.run(debug=False, host="0.0.0.0", port=port)
