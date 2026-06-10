import os
import json
from datetime import date

LIMITS_DIR = "/tmp/roofgrid_limits"
MAX_PER_EMAIL = 3
MAX_PER_IP_DAY = 3

# These are never rate-limited — add any test emails or IPs here
BYPASS_EMAILS = {"sam@thebizkeeper.com"}
BYPASS_IPS    = {"127.0.0.1", "::1", "localhost"}

_combos = None        # set of "email|address" — permanently blocked combos
_email_counts = None  # dict: email -> total report count
_ip_daily = None      # dict: ip -> {"count": N, "date": "YYYY-MM-DD"}


def _load():
    global _combos, _email_counts, _ip_daily
    os.makedirs(LIMITS_DIR, exist_ok=True)
    if _combos is None:
        try:
            with open(os.path.join(LIMITS_DIR, "combos.json")) as f:
                _combos = set(json.load(f))
        except Exception:
            _combos = set()
    if _email_counts is None:
        try:
            with open(os.path.join(LIMITS_DIR, "email_counts.json")) as f:
                _email_counts = json.load(f)
        except Exception:
            _email_counts = {}
    if _ip_daily is None:
        try:
            with open(os.path.join(LIMITS_DIR, "ip_daily.json")) as f:
                _ip_daily = json.load(f)
        except Exception:
            _ip_daily = {}


def _save():
    os.makedirs(LIMITS_DIR, exist_ok=True)
    with open(os.path.join(LIMITS_DIR, "combos.json"), "w") as f:
        json.dump(list(_combos), f)
    with open(os.path.join(LIMITS_DIR, "email_counts.json"), "w") as f:
        json.dump(_email_counts, f)
    with open(os.path.join(LIMITS_DIR, "ip_daily.json"), "w") as f:
        json.dump(_ip_daily, f)


def check_and_record(email, address, ip):
    """
    Returns (allowed: bool, reason: str).
    Call before generating a report. Records the attempt if allowed.
    """
    _load()
    today = date.today().isoformat()
    email_key = email.lower().strip()
    combo_key = f"{email_key}|{address.strip().lower()}"

    # Bypass for owner/test accounts — never blocked
    if email_key in BYPASS_EMAILS or ip in BYPASS_IPS:
        return True, ""

    # 1. Same email + same address — always blocked
    if combo_key in _combos:
        return False, "We already sent a report for this address to that email. Check your inbox."

    # 2. Email lifetime cap
    if _email_counts.get(email_key, 0) >= MAX_PER_EMAIL:
        return False, "You've used all 3 free reports. Contact us to upgrade for unlimited access."

    # 3. IP daily cap (resets each calendar day)
    ip_entry = _ip_daily.get(ip, {"count": 0, "date": today})
    if ip_entry["date"] != today:
        ip_entry = {"count": 0, "date": today}
    if ip_entry["count"] >= MAX_PER_IP_DAY:
        return False, "Daily limit reached. Come back tomorrow for more free reports."

    # All checks passed — record this attempt
    _combos.add(combo_key)
    _email_counts[email_key] = _email_counts.get(email_key, 0) + 1
    ip_entry["count"] += 1
    _ip_daily[ip] = ip_entry

    try:
        _save()
    except Exception as e:
        print(f"Rate limiter save error: {e}")

    return True, ""
