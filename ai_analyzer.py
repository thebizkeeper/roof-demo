import os
import json
import math
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


ZOOM = 19
IMG_W_PX = 600  # logical pixels (Mapbox base before @2x)
IMG_H_PX = 400


def _feet_per_pixel(lat):
    """Ground distance per logical pixel at zoom 19 for a given latitude."""
    meters = 156543.03392 * math.cos(math.radians(lat)) / (2 ** ZOOM)
    return meters * 3.28084  # convert to feet


def get_satellite_image_url(lng, lat, zoom=ZOOM):
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lng},{lat},{zoom},0/{IMG_W_PX}x{IMG_H_PX}@2x"
        f"?access_token={MAPBOX_TOKEN}"
    )


def analyze_roof(lat, lng, address, material):
    """Send satellite image to Claude Vision and return structured roof data."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    image_url = get_satellite_image_url(lng, lat)

    fpp = _feet_per_pixel(lat)
    img_w_ft = round(IMG_W_PX * fpp)
    img_h_ft = round(IMG_H_PX * fpp)

    prompt = f"""You are a professional roof measurement analyst reviewing a satellite image.

Property address: {address}

IMPORTANT SCALE INFORMATION:
- This image is {IMG_W_PX} x {IMG_H_PX} logical pixels
- Ground coverage: {img_w_ft} ft wide x {img_h_ft} ft tall
- Scale: 1 pixel = {fpp:.2f} feet ({fpp/3.28084:.3f} meters)

Use this scale to measure the roof accurately:
1. Estimate the roof outline in pixels (width and depth of each section)
2. Convert pixels to feet using the scale above
3. Calculate the flat footprint area in sq ft
4. Apply a pitch multiplier (low pitch: x1.05, moderate: x1.15, steep: x1.30) to get actual roof surface area

Respond ONLY with valid JSON in this exact format:
{{
  "sq_ft_estimate": <integer — actual roof surface area after pitch adjustment>,
  "sq_ft_low": <integer — 8% below estimate>,
  "sq_ft_high": <integer — 8% above estimate>,
  "facets": <integer — number of distinct roof sections/planes>,
  "pitch": <"low" | "moderate" | "steep">,
  "complexity": <"simple" | "moderate" | "complex">,
  "material_visible": <string — visible roofing material or "unknown">,
  "confidence": <"low" | "medium" | "high">,
  "notes": <string — 1-2 sentences about the roof>
}}

Measure only the main structure. Exclude detached garages and outbuildings."""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "url", "url": image_url},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    ai = json.loads(raw.strip())

    sq_ft = ai.get("sq_ft_estimate", 2500)
    complexity = ai.get("complexity", "moderate")
    costs = calculate_costs(sq_ft, material)
    timeline = calculate_timeline(sq_ft, complexity, address)

    return {
        "sq_ft": sq_ft,
        "sq_ft_low": ai.get("sq_ft_low", int(sq_ft * 0.9)),
        "sq_ft_high": ai.get("sq_ft_high", int(sq_ft * 1.1)),
        "facets": ai.get("facets", 4),
        "pitch": ai.get("pitch", "moderate"),
        "complexity": complexity.capitalize(),
        "material_visible": ai.get("material_visible", "unknown"),
        "confidence": ai.get("confidence", "medium"),
        "notes": ai.get("notes", ""),
        "satellite_image_url": image_url,
        **costs,
        "timeline": timeline,
    }


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
