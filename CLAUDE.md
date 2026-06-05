# RoofGrid AI — Project Notes

## What This Is
**RoofGrid AI is a SaaS roof measurement and estimation platform.**

A homeowner or contractor enters an address. The app captures a satellite image via Mapbox, sends it to Claude Vision AI for analysis, and emails a branded PDF report with:
- AI-estimated roof square footage
- Roof complexity and pitch
- Material and labor cost estimate range
- Estimated contractor completion timeline

**Target customers (paid subscribers):**
- Roofing contractors
- Insurance adjusters
- Property managers
- Solar companies

**Business model:** Freemium SaaS — modeled after roofr.com
- Free tier: homeowner enters address, gets 1 AI report emailed to them
- Pro tier ($49–99/mo): unlimited reports for contractors/adjusters
- Enterprise: custom pricing for insurance companies

**Not a white-label lead tool anymore.** Previously built as a lead capture demo to sell to individual roofing companies via Costin (WebGrit). Now pivoting to a standalone SaaS product owned and operated by Sam/The Biz Keeper.

## Live URLs
- **App:** https://www.roofgridai.com (also roofscan.up.railway.app)
- **GitHub:** https://github.com/thebizkeeper/roof-demo
- **Presentation:** https://roofscan.up.railway.app/static/presentation.html

## Tech Stack
- **Backend:** Python / Flask
- **Frontend:** Vanilla HTML/CSS/JS (single template: `templates/index.html`)
- **Maps:** Mapbox GL JS v3.3 + Mapbox Geocoder v5
- **AI Measurement:** Claude Vision API (Anthropic) — analyzes Mapbox satellite image
- **Report Delivery:** Resend.com — sends PDF from reports@roofgridai.com
- **PDF Generation:** ReportLab or WeasyPrint (Python)
- **Deployment:** Railway (auto-deploys from GitHub `main` branch)
- **Domain:** roofgridai.com (Cloudflare DNS → Railway)
- **Mapbox account:** thebizkeeper (Mapbox token in Railway env vars)

## Environment Variables (set in Railway dashboard)
| Variable | Value |
|---|---|
| `MAPBOX_TOKEN` | pk.eyJ1... (set in Railway) |
| `ANTHROPIC_API_KEY` | Claude Vision API key (to be added) |
| `RESEND_API_KEY` | Resend.com API key (to be added) |
| `NOTIFY_EMAIL` | sam@thebizkeeper.com (internal alerts) |
| `GMAIL_USER` | Gmail address (legacy, may replace with Resend) |
| `GMAIL_APP_PASSWORD` | 16-char Gmail App Password (legacy) |
| `GOOGLE_SHEETS_ID` | Sheet ID (not yet configured) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON (not yet configured) |

## Current App Flow (existing — no changes yet)
1. Address (Mapbox autocomplete)
2. Pin roof on satellite map
3. Ownership status
4. Roofing material selection
5. Scanning animation
6. Roof sq ft result (currently FAKE — random 2,200–3,400 sq ft placeholder)
7. Name
8. Email
9. Phone
→ Thank you page with cost estimate range + Start Over button

## Planned AI Report Flow (to be built)
1. Address entered → Mapbox captures satellite image at those coordinates
2. Image + metadata sent to Claude Vision API
3. Claude returns: sq ft estimate, complexity, pitch, facet count
4. Backend calculates: material cost range, labor cost range, contractor timeline
5. PDF report generated with RoofGrid AI branding
6. Report emailed from reports@roofgridai.com to the user

## AI Report Contents
```
RoofGrid AI — Roof Analysis Report
Report ID: RG-XXXXXX
Generated: [date]

Property: [address]

MEASUREMENTS
  Estimated Roof Area:     X,XXX sq ft
  Roof Sections (Facets):  X
  Pitch / Slope:           Low / Moderate / Steep
  Complexity:              Simple / Moderate / Complex

MATERIAL SELECTED
  [Asphalt / Metal / Tile / etc.]

COST ESTIMATE
  Materials:     $X,XXX – $X,XXX
  Labor:         $X,XXX – $X,XXX
  Total Range:   $X,XXX – $X,XXX

ESTIMATED COMPLETION TIMELINE
  Typical Duration:    X – X days  (or X – X weeks)
  Based on: [sq ft] · [complexity] · [region]

  * AI-generated estimate. For certified measurement, contact a licensed contractor.
```

## Timeline Logic (rule-based, no AI needed)
| Roof Size + Complexity | Timeline |
|---|---|
| Under 2,000 sq ft + Simple | 1 – 2 days |
| 2,000–2,800 sq ft + Moderate | 3 – 5 days |
| 2,800–3,500 sq ft + Moderate | 5 – 7 days |
| Large or Complex | 1 – 2 weeks |
| Very large / Multi-story / Complex | 2 – 3 weeks |
Weather note appended for Southeast region (Jun–Sep rainy season adds 1–3 days buffer).

## Cost Per Report (our cost)
- Mapbox satellite image: ~$0.001
- Claude Vision API analysis: ~$0.03–0.05
- Resend email delivery: free up to 100/day
- **Total: ~$0.03–0.06 per report**

## Build Phases
### Phase 1 — AI Measurement (next up)
- Replace fake random sq ft with Claude Vision satellite image analysis
- Add Resend email integration
- Generate and email PDF report to user
- Add ANTHROPIC_API_KEY and RESEND_API_KEY to Railway

### Phase 2 — Subscription / Payments
- Stripe integration for Pro plan signups
- User accounts and report history
- Rate limiting on free tier

### Phase 3 — Admin Dashboard
- Contractor login at /dashboard
- View all reports ordered
- Manage account and billing

## Key People
- **Sam Shukka** — The Biz Keeper (sam@thebizkeeper.com) — sole builder and owner of RoofGrid AI
- **Costin** — WebGrit — former partner on the lead capture demo version (no longer involved in this pivot)

## Open Items
1. Get Anthropic API key (claude.ai → API settings)
2. Sign up for Resend.com, verify roofgridai.com domain, get API key
3. Build Phase 1 (AI measurement + PDF report + email delivery)
4. Decide on pricing tiers before Phase 2
