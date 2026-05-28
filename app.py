from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "")

@app.route("/")
def index():
    return render_template("index.html", mapbox_token=MAPBOX_TOKEN)

@app.route("/api/lead", methods=["POST"])
def save_lead():
    data = request.get_json() or {}
    print("=== NEW ROOF LEAD ===")
    for k, v in data.items():
        print(f"  {k}: {v}")
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5300))
    app.run(debug=False, host="0.0.0.0", port=port)
