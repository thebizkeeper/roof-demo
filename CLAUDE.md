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

## Live URLs
- **App:** https://www.roofgridai.com
- **GitHub:** https://github.com/thebizkeeper/roof-demo
- **Railway auto-deploys from GitHub `main` branch**

## Tech Stack
- **Backend:** Python / Flask
- **Frontend:** Vanilla HTML/CSS/JS (`templates/index.html`)
- **Maps:** Mapbox GL JS v3.3 + Mapbox Geocoder v5 (zoom level 20)
- **AI Measurement:** Claude Vision API (`claude-opus-4-8`, `temperature=0`)
- **Report Delivery:** Resend.com — sends PDF from reports@roofgridai.com
- **PDF Generation:** ReportLab
- **Deployment:** Railway — Gunicorn with `--timeout 120 --workers 2`
- **Domain:** roofgridai.com (Cloudflare DNS → Railway)
- **Lead CRM:** Notion (daily databases: "Website Leads (Month DD, YYYY)")

## Environment Variables (all set in Railway dashboard)
| Variable | Status |
|---|---|
| `MAPBOX_TOKEN` | Set |
| `ANTHROPIC_API_KEY` | Set — NOTE: was exposed in chat, should be rotated |
| `RESEND_API_KEY` | Set |
| `NOTIFY_EMAIL` | sam@thebizkeeper.com |
| `NOTION_TOKEN` | Set |
| `NOTION_PARENT_PAGE_ID` | Set |
| `APP_URL` | https://www.roofgridai.com |

## Current App Flow (LIVE and working)
1. Address entry (Mapbox geocoder autocomplete)
2. Pin roof on satellite map
3. Ownership status selection
4. Roofing material selection
5. Scan animation → Claude Vision analyzes Mapbox satellite image
6. Roof sq ft result displayed (real AI measurement)
7. Name input
8. Email input
9. Phone input
→ Thank you page with cost estimate range + PDF report emailed + lead saved to Notion

## Key Files
- `app.py` — Flask routes: `/api/analyze` (scan step), `/api/report` (full pipeline), `/reports/<id>.pdf`
- `ai_analyzer.py` — Claude Vision call, address-based caching, cost/timeline calculations
- `report_generator.py` — ReportLab PDF generation
- `notion_leads.py` — Notion daily database creation + lead saving
- `templates/index.html` — Full frontend wizard (9 steps)
- `Procfile` — `gunicorn app:app --timeout 120 --workers 2`

## AI Measurement Approach
- Mapbox Static Images API: zoom 20 (@2x), 600×400 logical pixels
- Ground coverage at zoom 20: ~245ft × 164ft frame
- Claude prompt: give total ground sq ft, ask Claude what % of frame is the roof
- `temperature=0` for consistency
- Results cached by address string + material (30-day TTL, memory + disk)
- Accuracy: ±10–15% from actual — acceptable for a free estimate lead tool
- Scan result is locked per address in browser state — going Back and re-scanning reuses the same number

## Two-Endpoint AI Flow
- `/api/analyze` — called during scan animation, returns AI data only (no email/Notion)
- `/api/report` — called on final submit, uses pre-computed sqft from client (never re-runs AI), generates PDF, emails report, saves Notion lead, fires internal notification

## Notion Lead CRM
- New database created automatically on first submission each day: "Website Leads (Month DD, YYYY)"
- Columns: Full Name, Email, Phone, Address, Report ID, Material, Sq Ft, Cost Estimate, Source, Date, Report (URL)
- Report URL is UUID-based (32-char hex, unguessable) for privacy
- No duplicate filtering (removed — was blocking re-tests with same email)

## PDF Report
- Branded header: RoofGrid AI dark/green theme
- Sections: Measurements, Material Selected, Cost Estimate, Estimated Completion Timeline
- No satellite image in PDF (removed by user preference)
- Disclaimer footer
- Served from `/tmp/roofgrid_reports/` (ephemeral — Railway clears on redeploy)

## Cost Per Report (our cost)
- Mapbox satellite image: ~$0.001
- Claude Vision API analysis: ~$0.03–0.05
- Resend email delivery: free up to 100/day
- **Total: ~$0.03–0.06 per report**

## Known Issues / Watch List
- **ANTHROPIC_API_KEY should be rotated** — was exposed in a chat session
- **PDF storage is ephemeral** — `/tmp/` clears on Railway redeploys. Report links in Notion break after redeploy. Fix: migrate to Cloudflare R2 or S3 for permanent storage.
- **AI accuracy ~±10–15%** — Claude Vision is not a certified measurement tool. For production at scale, consider EagleView API ($8–12/report) as an upgrade path.

## Build Phases
### Phase 1 — AI Measurement ✅ COMPLETE
- Claude Vision satellite image analysis
- Resend email with PDF attachment
- Notion lead CRM with daily databases
- Address-based measurement caching

### Phase 2 — Subscription / Payments (NEXT)
- Stripe integration for Pro plan ($49–99/mo)
- Contractor accounts + login
- Rate limiting on free tier (1 report per email)
- Report history per account

### Phase 3 — Admin Dashboard
- Contractor login at /dashboard
- View all reports, manage billing

## Revenue Model
- **Lead selling (near-term):** Export Notion CSV → sell homeowner leads to local contractors
- **Pro subscriptions (main SaaS):** Contractors pay $49–99/mo for unlimited reports
- **Enterprise:** Insurance adjusters / property managers, custom pricing

## Key People
- **Sam Shukka** — The Biz Keeper (sam@thebizkeeper.com) — sole builder and owner
- **Costin** — WebGrit — former partner on the old lead capture demo (no longer involved)
