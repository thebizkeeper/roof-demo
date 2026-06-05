from flask import Flask, render_template, request, jsonify
import os, threading, uuid
from datetime import datetime

import resend

from ai_analyzer import analyze_roof, get_satellite_image_url
from report_generator import generate_pdf_report
from notion_leads import save_lead

try:
    import gspread
    from google.oauth2.service_account import Credentials
    import json as _json
    GSPREAD_OK = True
except ImportError:
    GSPREAD_OK = False

app = Flask(__name__)

MAPBOX_TOKEN       = os.environ.get("MAPBOX_TOKEN", "")
NOTIFY_EMAIL       = os.environ.get("NOTIFY_EMAIL", "sam@thebizkeeper.com")
RESEND_API_KEY     = os.environ.get("RESEND_API_KEY", "")
SHEETS_ID          = os.environ.get("GOOGLE_SHEETS_ID", "")
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

resend.api_key = RESEND_API_KEY


def make_report_id():
    return "RG-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()


def send_report_email(to_email, to_name, address, report_id, pdf_bytes):
    """Email the PDF report to the homeowner via Resend."""
    if not RESEND_API_KEY:
        print("Resend not configured — skipping report email")
        return
    try:
        resend.Emails.send({
            "from": "RoofGrid AI <reports@roofgridai.com>",
            "to": [to_email],
            "subject": f"Your Roof Analysis Report — {address}",
            "html": f"""
            <div style="font-family:sans-serif;max-width:560px;margin:0 auto">
              <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
                <h2 style="color:#10b981;margin:0;font-size:20px">RoofGrid AI</h2>
                <p style="color:#94a3b8;margin:6px 0 0">Roof Analysis Report</p>
              </div>
              <div style="border:1px solid #e2e8f0;border-top:none;padding:28px;border-radius:0 0 10px 10px">
                <p style="color:#0f172a">Hi {to_name},</p>
                <p style="color:#374151">Your AI-powered roof analysis report for
                  <strong>{address}</strong> is attached to this email.</p>
                <p style="color:#374151">The report includes:</p>
                <ul style="color:#374151;padding-left:20px;line-height:1.8">
                  <li>AI-estimated roof square footage</li>
                  <li>Roof complexity and pitch</li>
                  <li>Material and labor cost range</li>
                  <li>Estimated contractor completion timeline</li>
                </ul>
                <p style="color:#64748b;font-size:13px;margin-top:24px">
                  Report ID: {report_id}<br>
                  Generated: {datetime.now().strftime("%B %d, %Y")}
                </p>
                <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">
                <p style="color:#94a3b8;font-size:12px">
                  Powered by RoofGrid AI · roofgridai.com<br>
                  This is an AI-generated estimate. For certified measurements, contact a licensed contractor.
                </p>
              </div>
            </div>
            """,
            "attachments": [{
                "filename": f"RoofGrid-Report-{report_id}.pdf",
                "content": list(pdf_bytes),
            }],
        })
        print(f"Report emailed to {to_email} OK")
    except Exception as e:
        print(f"Resend email error: {e}")


def notify_internal(data, report_id):
    """Send internal lead notification to sam@thebizkeeper.com."""
    if not RESEND_API_KEY:
        return
    try:
        sq_ft = data.get("sq_ft", 0)
        resend.Emails.send({
            "from": "RoofGrid AI <reports@roofgridai.com>",
            "to": [NOTIFY_EMAIL],
            "subject": f"New Lead — {data.get('name','Unknown')} | {data.get('address','')}",
            "html": f"""
            <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
              <div style="background:#0f172a;padding:20px 28px;border-radius:10px 10px 0 0">
                <h2 style="color:#10b981;margin:0">New RoofGrid AI Lead</h2>
              </div>
              <div style="border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
                <table style="width:100%;border-collapse:collapse">
                  <tr><td style="padding:7px 0;color:#64748b;width:130px">Name</td><td style="font-weight:600">{data.get('name','')}</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Email</td><td>{data.get('email','')}</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Phone</td><td style="font-weight:600">{data.get('phone','')}</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Address</td><td>{data.get('address','')}</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Roof Size</td><td style="font-weight:600;color:#1a56db">{sq_ft:,} sq ft</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Material</td><td>{data.get('material','')}</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Est. Cost</td><td>${data.get('cost_total_low',0):,} – ${data.get('cost_total_high',0):,}</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Timeline</td><td>{data.get('timeline',{}).get('range','N/A')}</td></tr>
                  <tr><td style="padding:7px 0;color:#64748b">Report ID</td><td style="font-size:12px;color:#64748b">{report_id}</td></tr>
                </table>
              </div>
            </div>
            """,
        })
    except Exception as e:
        print(f"Internal notify error: {e}")


def save_to_sheets(data, report_id):
    if not GSPREAD_OK or not SERVICE_ACCOUNT_JSON or not SHEETS_ID:
        return
    try:
        creds = Credentials.from_service_account_info(
            _json.loads(SERVICE_ACCOUNT_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        ws = gspread.authorize(creds).open_by_key(SHEETS_ID).sheet1
        if not ws.get_all_values():
            ws.append_row(["Report ID","Name","Email","Phone","Address","Sq Ft",
                           "Material","Cost Low","Cost High","Timeline","Date"])
        ws.append_row([
            report_id,
            data.get("name",""),
            data.get("email",""),
            data.get("phone",""),
            data.get("address",""),
            data.get("sq_ft",""),
            data.get("material",""),
            data.get("cost_total_low",""),
            data.get("cost_total_high",""),
            data.get("timeline",{}).get("range",""),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ])
    except Exception as e:
        print(f"Sheets error: {e}")


@app.route("/")
def index():
    return render_template("index.html", mapbox_token=MAPBOX_TOKEN)


@app.route("/api/analyze", methods=["POST"])
def analyze_only():
    """Lightweight endpoint: runs AI analysis only, no email or Notion. Called during scan animation."""
    body = request.get_json() or {}
    lat  = body.get("lat")
    lng  = body.get("lng")
    if not lat or not lng:
        return jsonify({"ok": False, "error": "Missing coordinates"}), 400
    try:
        ai = analyze_roof(lat, lng, body.get("address", ""), body.get("material", "Asphalt Shingle"))
        return jsonify({"ok": True, **ai})
    except Exception as e:
        print(f"Analyze error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/report", methods=["POST"])
def create_report():
    """
    Full pipeline: AI analysis → PDF → email to user → save Notion lead → notify internally.
    Expected JSON: address, lat, lng, material, name, email, phone, ownership
    """
    body = request.get_json() or {}
    address  = body.get("address", "")
    lat      = body.get("lat")
    lng      = body.get("lng")
    material = body.get("material", "Asphalt Shingle")
    name     = body.get("name", "")
    email    = body.get("email", "")
    phone    = body.get("phone", "")
    ownership= body.get("ownership", "")

    if not lat or not lng:
        return jsonify({"ok": False, "error": "Missing coordinates"}), 400

    report_id = make_report_id()

    # Use pre-computed AI data from client if available (avoids running AI twice)
    if body.get("sqft") and body.get("cost_total_low"):
        ai = {
            "sq_ft":           body["sqft"],
            "sq_ft_low":       body.get("sqft_low", int(body["sqft"] * 0.9)),
            "sq_ft_high":      body.get("sqft_high", int(body["sqft"] * 1.1)),
            "facets":          body.get("facets", 4),
            "pitch":           body.get("pitch", "moderate"),
            "complexity":      body.get("complexity", "Moderate"),
            "material_visible":"unknown",
            "confidence":      "medium",
            "notes":           "",
            "satellite_image_url": get_satellite_image_url(lng, lat),
            "cost_mat_low":    body.get("cost_mat_low", 0),
            "cost_mat_high":   body.get("cost_mat_high", 0),
            "cost_labor_low":  body.get("cost_labor_low", 0),
            "cost_labor_high": body.get("cost_labor_high", 0),
            "cost_total_low":  body["cost_total_low"],
            "cost_total_high": body["cost_total_high"],
            "timeline":        body.get("timeline", {"range": "3 – 5 days", "weather_note": ""}),
        }
    else:
        try:
            ai = analyze_roof(lat, lng, address, material)
        except Exception as e:
            print(f"AI analysis error: {e}")
            ai = {
                "sq_ft": 2500, "sq_ft_low": 2250, "sq_ft_high": 2750,
                "facets": 4, "pitch": "moderate", "complexity": "Moderate",
                "material_visible": "unknown", "confidence": "low",
                "notes": "AI analysis unavailable — estimate based on average.",
                "satellite_image_url": "",
                "cost_mat_low": 3750, "cost_mat_high": 5000,
                "cost_labor_low": 2500, "cost_labor_high": 3750,
                "cost_total_low": 6250, "cost_total_high": 8750,
                "timeline": {"range": "3 – 5 days", "weather_note": ""},
            }

    full_data = {
        "name": name, "email": email, "phone": phone,
        "address": address, "material": material, "ownership": ownership,
        "source": "Free Report",
        **ai,
    }

    print(f"=== NEW REPORT {report_id} === {name} | {address}")

    # Generate PDF
    try:
        pdf_bytes = generate_pdf_report(full_data, report_id)
    except Exception as e:
        print(f"PDF generation error: {e}")
        pdf_bytes = None

    # Fire all delivery tasks in background threads so response is fast
    if pdf_bytes and email:
        threading.Thread(
            target=send_report_email,
            args=(email, name, address, report_id, pdf_bytes),
            daemon=True
        ).start()

    threading.Thread(target=notify_internal, args=(full_data, report_id), daemon=True).start()
    threading.Thread(target=save_lead,       args=(full_data, report_id), daemon=True).start()
    threading.Thread(target=save_to_sheets,  args=(full_data, report_id), daemon=True).start()

    return jsonify({
        "ok":        True,
        "report_id": report_id,
        "sq_ft":     ai["sq_ft"],
        "sq_ft_low": ai["sq_ft_low"],
        "sq_ft_high":ai["sq_ft_high"],
        "complexity":ai["complexity"],
        "pitch":     ai["pitch"],
        "cost_total_low":  ai["cost_total_low"],
        "cost_total_high": ai["cost_total_high"],
        "cost_mat_low":    ai["cost_mat_low"],
        "cost_mat_high":   ai["cost_mat_high"],
        "cost_labor_low":  ai["cost_labor_low"],
        "cost_labor_high": ai["cost_labor_high"],
        "timeline":  ai["timeline"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5300))
    app.run(debug=False, host="0.0.0.0", port=port)
