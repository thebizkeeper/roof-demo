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


def save_lead(data, report_id):
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

        resp = requests.post(
            f"{NOTION_API}/pages",
            headers=_headers(),
            json={
                "parent": {"database_id": db_id},
                "properties": {
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
                },
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            print(f"Notion lead saved OK — {report_id}")
        else:
            print(f"Notion error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"Notion exception: {e}")
