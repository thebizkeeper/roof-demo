import io
import os
import requests
from datetime import datetime

NOTION_TOKEN          = os.environ.get("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")

NOTION_API  = "https://api.notion.com/v1"
NOTION_VER  = "2022-06-28"


def _headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VER,
    }


def _upload_pdf(pdf_bytes, report_id):
    """Upload PDF bytes to Notion file storage. Returns file_upload id or None."""
    filename = f"RoofGrid-{report_id}.pdf"
    try:
        # Step 1 — initiate upload
        r1 = requests.post(
            f"{NOTION_API}/file_uploads",
            headers=_headers(),
            json={"name": filename, "content_type": "application/pdf"},
            timeout=15,
        )
        upload = r1.json()
        upload_id = upload.get("id")
        if not upload_id:
            print(f"Notion file upload init failed: {upload}")
            return None

        # Step 2 — send file data
        r2 = requests.put(
            f"{NOTION_API}/file_uploads/{upload_id}/parts",
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": NOTION_VER,
            },
            files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
            timeout=30,
        )
        if r2.status_code not in (200, 201):
            print(f"Notion file upload parts failed: {r2.status_code} {r2.text[:200]}")
            return None

        # Step 3 — complete upload
        r3 = requests.post(
            f"{NOTION_API}/file_uploads/{upload_id}/complete",
            headers=_headers(),
            timeout=15,
        )
        if r3.status_code not in (200, 201):
            print(f"Notion file upload complete failed: {r3.status_code}")
            return None

        print(f"Notion PDF uploaded OK — {upload_id}")
        return upload_id

    except Exception as e:
        print(f"Notion PDF upload exception: {e}")
        return None


def _today_title():
    return f"Website Leads ({datetime.utcnow().strftime('%B %d, %Y')})"


def get_or_create_daily_database():
    """Find today's database under the parent page, or create it."""
    title = _today_title()

    # Search for an existing database with today's title
    resp = requests.post(
        f"{NOTION_API}/search",
        headers=_headers(),
        json={"query": title, "filter": {"property": "object", "value": "database"}},
        timeout=10,
    )
    for result in resp.json().get("results", []):
        db_title = ""
        title_arr = result.get("title", [])
        if title_arr:
            db_title = title_arr[0].get("plain_text", "")
        if db_title == title:
            return result["id"]

    # Not found — create a new database for today
    create_resp = requests.post(
        f"{NOTION_API}/databases",
        headers=_headers(),
        json={
            "parent": {"type": "page_id", "page_id": NOTION_PARENT_PAGE_ID},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": {
                "Full Name":     {"title": {}},
                "Email":         {"email": {}},
                "Phone":         {"phone_number": {}},
                "Address":       {"rich_text": {}},
                "Report ID":     {"rich_text": {}},
                "Material":      {"select": {}},
                "Sq Ft":         {"number": {}},
                "Cost Estimate": {"rich_text": {}},
                "Source":        {"select": {}},
                "Date":          {"date": {}},
            },
        },
        timeout=10,
    )
    data = create_resp.json()
    if "id" not in data:
        raise Exception(f"Failed to create Notion database: {data}")
    print(f"Created Notion database: {title}")
    return data["id"]


def is_duplicate(database_id, email):
    """Return True if this email already has an entry in today's database."""
    if not email:
        return False
    resp = requests.post(
        f"{NOTION_API}/databases/{database_id}/query",
        headers=_headers(),
        json={"filter": {"property": "Email", "email": {"equals": email}}},
        timeout=10,
    )
    return len(resp.json().get("results", [])) > 0


def save_lead(data, report_id, pdf_bytes=None):
    if not NOTION_TOKEN or not NOTION_PARENT_PAGE_ID:
        print("Notion not configured — skipping lead save")
        return

    try:
        db_id = get_or_create_daily_database()

        email = data.get("email", "")
        if is_duplicate(db_id, email):
            print(f"Duplicate lead skipped: {email}")
            return

        total_low  = data.get("cost_total_low",  0)
        total_high = data.get("cost_total_high", 0)
        cost_range = f"${total_low:,} – ${total_high:,}" if total_low else "N/A"

        # Build Report file property — upload actual PDF if bytes provided
        report_prop = None
        if pdf_bytes:
            upload_id = _upload_pdf(pdf_bytes, report_id)
            if upload_id:
                report_prop = {
                    "files": [{
                        "name": f"RoofGrid-{report_id}.pdf",
                        "type": "file_upload",
                        "file_upload": {"id": upload_id},
                    }]
                }
        if not report_prop and data.get("report_url"):
            report_prop = {
                "files": [{
                    "name": f"RoofGrid-{report_id}.pdf",
                    "type": "external",
                    "external": {"url": data["report_url"]},
                }]
            }

        properties = {
            "Full Name":     {"title":        [{"text": {"content": data.get("name", "Unknown")}}]},
            "Email":         {"email":         data.get("email") or None},
            "Phone":         {"phone_number":  data.get("phone") or None},
            "Address":       {"rich_text":     [{"text": {"content": data.get("address", "")}}]},
            "Report ID":     {"rich_text":     [{"text": {"content": report_id}}]},
            "Material":      {"select":        {"name": data.get("material", "Unknown")}},
            "Sq Ft":         {"number":        int(data.get("sq_ft", 0)) or None},
            "Cost Estimate": {"rich_text":     [{"text": {"content": cost_range}}]},
            "Source":        {"select":        {"name": data.get("source", "Free Report")}},
            "Date":          {"date":          {"start": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}},
        }
        if report_prop:
            properties["Report"] = report_prop

        resp = requests.post(
            f"{NOTION_API}/pages",
            headers=_headers(),
            json={"parent": {"database_id": db_id}, "properties": properties},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            print(f"Notion lead saved OK — {report_id}")
        else:
            print(f"Notion error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"Notion exception: {e}")
