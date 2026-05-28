# RoofScan Pro — Project Notes

## What This Is
A lead capture demo app for roofing companies. Homeowners enter their address, go through a 9-step guided flow, and submit their name/email/phone. The roofing company receives the lead via email and Google Sheets/Notion.

Built by The Biz Keeper (Sam) to sell to roofing clients sourced by Costin (WebGrit).

## Live URLs
- **App:** https://roofscan.up.railway.app
- **GitHub:** https://github.com/thebizkeeper/roof-demo
- **Presentation:** https://roofscan.up.railway.app/static/presentation.html

## Tech Stack
- **Backend:** Python / Flask
- **Frontend:** Vanilla HTML/CSS/JS (single template: `templates/index.html`)
- **Maps:** Mapbox GL JS v3.3 + Mapbox Geocoder v5
- **Deployment:** Railway (auto-deploys from GitHub `main` branch)
- **Mapbox account:** thebizkeeper (Mapbox token in Railway env vars)

## Environment Variables (set in Railway dashboard)
| Variable | Value |
|---|---|
| `MAPBOX_TOKEN` | pk.eyJ1... (set in Railway) |
| `NOTIFY_EMAIL` | sam@thebizkeeper.com (temporary — will be client's email) |
| `GMAIL_USER` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | 16-char Gmail App Password |
| `GOOGLE_SHEETS_ID` | Sheet ID (not yet configured) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON (not yet configured) |

## Lead Flow
1. Address (Mapbox autocomplete)
2. Pin roof on satellite map
3. Ownership status
4. Roofing material selection
5. Scanning animation
6. Roof sq ft result (currently random 2,200–3,400 sq ft — placeholder)
7. Name
8. Email
9. Phone
→ Thank you page with cost estimate range + Start Over button

## Lead Delivery (built, needs env vars)
- Email notification to `NOTIFY_EMAIL` via Gmail SMTP
- Notion integration (to be configured)

## Open Questions / Decisions Needed
See bottom of this file.

---

## Open Questions

### 1. Roof Measurement Tool
**Decision needed by: Costin + client**
Current measurement is a random number (2,200–3,400 sq ft). Options:
- A) Keep as demo placeholder — rep visits for real measurement
- B) Use property lot size from a free real estate API as a proxy
- C) Upgrade to EagleView or Nearmap (paid per-measurement, what big companies use)

### 2. Final Results Page — Show Price or Not?
**Decision needed by: Costin + client**
- A) Show cost estimate range to homeowner on screen (current behavior)
- B) Show "An estimate will be emailed to you within 24 hours" — client sends manually
  → If B: build admin panel where client enters their material/labor rates and the app calculates the estimate for them to review and send

### 3. Admin Dashboard
**Planned feature (build after client decides on #2)**
Private login at `/admin` for the roofing company client. Will include:
- Update notification email address
- Set material costs per sq ft (Asphalt, Metal, Tile, etc.)
- Set labor rate
- View all leads
- Edit and send estimates to homeowners

### 4. Lead Storage — Notion
**Action needed: Sam**
Set up Notion integration for lead logging. Needs:
- Notion account + database created
- Notion API key → add to Railway as `NOTION_TOKEN`
- Database ID → add to Railway as `NOTION_DATABASE_ID`

### 5. Email Notifications
**Action needed: Sam**
Gmail App Password not yet configured. Needs:
- Google account 2-step verification enabled
- App Password generated (Google Account → Security → App Passwords)
- Add to Railway: `GMAIL_USER` and `GMAIL_APP_PASSWORD`

### 6. Custom Domain (future)
Currently at roofscan.up.railway.app. When selling to a client, set up their own domain (e.g. roof.theirclientdomain.com) pointing to Railway.

### 7. White-Labeling for Each Client
When selling to multiple roofing companies, each deployment will need:
- Their company name, logo, colors
- Their phone number
- Their notification email
- Their pricing rates
Consider making these all env vars so one codebase serves multiple clients.

## Key People
- **Sam Shukka** — The Biz Keeper (sam@thebizkeeper.com) — builds and sells the tool
- **Costin** — WebGrit — has the roofing client relationship
- **Client** — roofing company (name TBD) — end buyer of this tool
