import os
import json
import time as _time
import hashlib
import base64
import requests
import anthropic

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MATERIAL_RATES = {
    "Asphalt Shingle": {"mat_low": 1.50, "mat_high": 2.00, "labor_low": 1.00, "labor_high": 1.50},
    "Metal":           {"mat_low": 5.00, "mat_high": 12.00,"labor_low": 3.00, "labor_high": 5.00},
    "Tile":            {"mat_low": 4.00, "mat_high": 8.00, "labor_low": 3.00, "labor_high": 6.00},
    "Wood Shake":      {"mat_low": 3.00, "mat_high": 6.00, "labor_low": 2.00, "labor_high": 4.00},
    "Flat / TPO":      {"mat_low": 2.00, "mat_high": 4.00, "labor_low": 1.50, "labor_high": 3.00},
}

SOUTHEAST_STATES = {"FL", "GA", "AL", "MS", "LA", "SC", "NC"}

CACHE_DIR = "/tmp/roofgrid_cache"
CACHE_TTL = 30 * 24 * 3600  # 30 days

# In-process memory cache — survives across requests within the same Gunicorn worker
_MEM_CACHE: dict = {}


def _cache_key(address, material):
    # Key on address string, not lat/lng — map marker position varies slightly between runs
    return hashlib.md5(f"{address.strip().lower()}|{material}".encode()).hexdigest()


def _read_cache(address, material):
    key = _cache_key(address, material)
    # 1. Memory cache (instant, per-worker)
    if key in _MEM_CACHE:
        return dict(_MEM_CACHE[key])
    # 2. Disk cache (survives worker restarts, shared across workers)
    try:
        with open(os.path.join(CACHE_DIR, key + ".json")) as f:
            data = json.load(f)
        if _time.time() - data.pop("_ts", 0) < CACHE_TTL:
            _MEM_CACHE[key] = data
            return dict(data)
    except Exception:
        pass
    return None


def _write_cache(address, material, result):
    key = _cache_key(address, material)
    _MEM_CACHE[key] = result
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(os.path.join(CACHE_DIR, key + ".json"), "w") as f:
            json.dump({**result, "_ts": _time.time()}, f)
    except Exception:
        pass


ZOOM = 19
IMG_W_PX = 600
IMG_H_PX = 400


def get_satellite_image_url(lng, lat, zoom=ZOOM):
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lng},{lat},{zoom},0/{IMG_W_PX}x{IMG_H_PX}@2x"
        f"?access_token={MAPBOX_TOKEN}"
    )


def analyze_roof(lat, lng, address, material):
    """Send satellite image to Claude Vision and return structured roof data."""
    # Return cached result so the same address always gives the same number
    cached = _read_cache(address, material)
    if cached:
        cached["satellite_image_url"] = get_satellite_image_url(lng, lat)
        print(f"Cache hit: {address}")
        return cached

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    image_url = get_satellite_image_url(lng, lat)

    prompt = f"""You are a professional roof measurement analyst reviewing a satellite image.

Property address: {address}

Analyze the roof visible in this satellite image and respond ONLY with valid JSON in this exact format:
{{
  "sq_ft_estimate": <integer — your best estimate of roof area in square feet>,
  "sq_ft_low": <integer — conservative low end, roughly 10% below estimate>,
  "sq_ft_high": <integer — high end, roughly 10% above estimate>,
  "facets": <integer — number of distinct roof sections/planes>,
  "pitch": <"low" | "moderate" | "steep">,
  "complexity": <"simple" | "moderate" | "complex">,
  "material_visible": <string — what material appears visible, or "unknown">,
  "confidence": <"low" | "medium" | "high">,
  "notes": <string — 1-2 sentences about the roof structure>
}}

Focus only on the main structure's roof at the given address. Do not include detached garages or outbuildings unless clearly attached."""

    # Fetch image server-side — Mapbox robots.txt blocks Claude from fetching it directly
    img_resp = requests.get(image_url, timeout=15)
    img_b64 = base64.standard_b64encode(img_resp.content).decode("utf-8")

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    ai = json.loads(raw.strip())

    sq_ft = ai.get("sq_ft_estimate") or 2500
    complexity = ai.get("complexity") or "moderate"
    pitch = ai.get("pitch") or "moderate"
    costs = calculate_costs(sq_ft, material)
    timeline = calculate_timeline(sq_ft, complexity, address)

    result = {
        "sq_ft": sq_ft,
        "sq_ft_low": ai.get("sq_ft_low") or int(sq_ft * 0.92),
        "sq_ft_high": ai.get("sq_ft_high") or int(sq_ft * 1.08),
        "facets": ai.get("facets") or 4,
        "pitch": pitch,
        "complexity": complexity.capitalize(),
        "material_visible": ai.get("material_visible") or "unknown",
        "confidence": ai.get("confidence") or "medium",
        "notes": ai.get("notes") or "",
        "satellite_image_url": image_url,
        **costs,
        "timeline": timeline,
    }
    _write_cache(address, material, result)
    return result


def calculate_costs(sq_ft, material):
    rates = MATERIAL_RATES.get(material, MATERIAL_RATES["Asphalt Shingle"])
    mat_low  = int(sq_ft * rates["mat_low"])
    mat_high = int(sq_ft * rates["mat_high"])
    lab_low  = int(sq_ft * rates["labor_low"])
    lab_high = int(sq_ft * rates["labor_high"])
    return {
        "cost_mat_low":   mat_low,
        "cost_mat_high":  mat_high,
        "cost_labor_low": lab_low,
        "cost_labor_high":lab_high,
        "cost_total_low": mat_low + lab_low,
        "cost_total_high":mat_high + lab_high,
    }


def calculate_timeline(sq_ft, complexity, address):
    address_upper = address.upper()
    state = ""
    for part in address_upper.split(","):
        part = part.strip()
        if len(part) == 2 and part.isalpha():
            state = part
            break

    in_southeast = state in SOUTHEAST_STATES

    if sq_ft < 2000 and complexity == "simple":
        base = "1 – 2 days"
    elif sq_ft < 2800 and complexity in ["simple", "moderate"]:
        base = "3 – 5 days"
    elif sq_ft < 3500 and complexity == "moderate":
        base = "5 – 7 days"
    elif complexity == "complex" or sq_ft >= 3500:
        base = "1 – 2 weeks"
    else:
        base = "2 – 3 weeks"

    note = ""
    if in_southeast:
        note = "Florida/Southeast rainy season (Jun–Sep) may add 1–3 days."

    return {"range": base, "weather_note": note}
