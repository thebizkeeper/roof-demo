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
- **Maps:** Mapbox GL JS v3.3 + Mapbox Geocoder v5 (zoom level 19)
- **AI Measurement:** Claude Vision API (`claude-opus-4-8`) — no temperature param (deprecated on this model)
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
6. Roof sq ft result displayed — "Approx. X sq ft" with estimated range (low–high)
7. Name input
8. Email input
9. Phone input
→ Thank you page with report summary checklist + PDF report emailed + lead saved to Notion

## Key Files
- `app.py` — Flask routes: `/` (landing page), `/app` (tool wizard), `/api/analyze`, `/api/report`, `/reports/<id>.pdf`
- `ai_analyzer.py` — Claude Vision call, address-based caching, cost/timeline calculations
- `report_generator.py` — ReportLab PDF generation
- `notion_leads.py` — Notion daily database creation + lead saving
- `templates/landing.html` — Marketing homepage at `/`
- `templates/index.html` — Full frontend wizard at `/app` (10 steps including thank you)
- `Procfile` — `gunicorn app:app --timeout 120 --workers 2`

## AI Measurement Approach
- Mapbox Static Images API: **zoom 19** (@2x), 600×400 logical pixels
- **IMPORTANT — zoom 19 is intentional.** We tested zoom 20 (tighter frame) and it caused Claude to overestimate. Zoom 19 gives more surrounding context which improves Claude's spatial calibration. Do not change back to zoom 20.
- Image is fetched **server-side** as base64 and passed to Claude — Mapbox robots.txt blocks Claude from fetching image URLs directly
- **Simple open-ended prompt** — no pixel math, no scale formulas. Just "estimate the roof sq ft." Claude's trained intuition on satellite imagery outperforms any manual scale calculation we've tried.
- Results cached by address string + material (30-day TTL, in-memory + disk at `/tmp/roofgrid_cache/`)
- Accuracy: ~±500 sq ft / ±20% — acceptable for a free estimate lead tool
- Scan result is locked per address in browser (`scannedAddress` variable) — going Back and re-scanning reuses the cached number

## Two-Endpoint AI Flow
- `/api/analyze` — called during scan animation, returns AI data only (no email/Notion)
- `/api/report` — called on final submit, uses pre-computed sqft from client (never re-runs AI), generates PDF, emails report, saves Notion lead, fires internal notification

## Step 6 — Measurement Display
- Shows: "Approx. **X,XXX** square feet of roof area"
- Shows estimated range below: "Estimated range: X,XXX – X,XXX sq ft"
- Shows: "Includes pitch factor · Based on satellite imagery"

## Thank You Page (Step 10)
- Replaced big cost-range hero number with a "YOUR REPORT INCLUDES:" checklist:
  - Roof measurement (sq ft)
  - Material assessment
  - Cost estimate range ($low – $high)
  - Estimated timeline
- Then shows Address and Email below
- Cost detail is still in the PDF — the checklist format is less alarming than a standalone big dollar number

## Cost Rates (per sq ft, verified accurate)
| Material | Mat Low | Mat High | Labor Low | Labor High | Total Range |
|---|---|---|---|---|---|
| Asphalt Shingle | $1.50 | $2.00 | $1.00 | $1.50 | $2.50–$3.50/sq ft |
| Metal | $5.00 | $12.00 | $3.00 | $5.00 | $8–$17/sq ft |
| Tile | $4.00 | $8.00 | $3.00 | $6.00 | $7–$14/sq ft |
| Wood Shake | $3.00 | $6.00 | $2.00 | $4.00 | $5–$10/sq ft |
| Flat / TPO | $2.00 | $4.00 | $1.50 | $3.00 | $3.50–$7/sq ft |

Tile is genuinely $10–20/sq ft in the real market — our rates are slightly conservative, not high.

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
- **AI accuracy ~±20%** — Claude Vision is not a certified measurement tool. Acceptable for free lead-gen tier. For production Pro tier, consider EagleView API ($8–12/report) as an upgrade path.
- **Cache clears on Railway restart** — in-memory cache (`_MEM_CACHE`) and disk cache (`/tmp/roofgrid_cache/`) both clear. First scan after restart re-runs Claude and re-populates cache.

## Build Phases
### Phase 1 — AI Measurement ✅ COMPLETE
- Claude Vision satellite image analysis (zoom 19, base64, simple prompt)
- Resend email with PDF attachment
- Notion lead CRM with daily databases
- Address-based measurement caching (memory + disk)
- Scan lock (client-side `scannedAddress` prevents re-scan on Back)
- Measurement display with "approx." and estimated range
- Thank you page with report summary checklist
- Marketing homepage (`/`) with hero, how-it-works, why section, FAQ, CTA footer
- Tool moved to `/app` — logo anchored top-left on desktop, centered top on mobile
- Desktop hero: logo top-left, headline centered vertically, house image blends into gradient
- Mobile hero: logo centered at top (`margin:0 auto`, `display:block`), 48px gap before headline, 1.8rem headline, button centered (`align-self:center`), stars top-aligned (`align-items:flex-start`)
- Footer: © 2026, white/light text, no logo, spam folder notice, Terms & Privacy link

## Legal & Compliance
- Terms of Service + Privacy Policy at `/terms` — covers AI accuracy disclaimer, lead sharing disclosure, no warranty, limitation of liability
- Consent checkbox on Step 9 (required to submit): "I agree to the Terms of Service and Privacy Policy and authorize follow-up regarding my estimate."
- Lead sharing disclosed in Terms sections 8 & 9 — satisfies TCPA written consent requirement
- Rate limiting: 3 reports/email (lifetime), 3 reports/IP/day, same email+address blocked permanently
- Bypass whitelist: `sam@thebizkeeper.com` and localhost never rate-limited
- `rate_limiter.py` — stores limits in `/tmp/roofgrid_limits/` (clears on Railway redeploy — acceptable for rate limiting)

### Phase 2 — Subscription / Payments (ON HOLD — not started)
**Do not build Phase 2 until lead revenue is flowing.** Near-term focus is driving traffic and selling leads.
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
