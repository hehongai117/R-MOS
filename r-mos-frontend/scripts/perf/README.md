# R-MOS Lighthouse Performance Runbook

Measures Web Vitals (FCP / LCP / TBT / CLS / TTI) and the Lighthouse Performance score for key R-MOS frontend routes. Output is a markdown table ready to paste into the phase4 baseline doc, plus raw JSON files for archiving.

---

## Prerequisites

### 1. Install Lighthouse + chrome-launcher (dev-only, on demand)

These packages are **not** included in `package.json` to avoid bloating CI installs. Install them once, locally:

```bash
cd r-mos-frontend
npm i -D lighthouse chrome-launcher
```

> They are not committed to `package.json`. Re-install if you do a fresh `npm ci`.

### 2. Google Chrome / Chromium

The script launches headless Chrome via `chrome-launcher`. Make sure `google-chrome`, `chromium`, or `chromium-browser` is on your `PATH`. On macOS, Chrome in `/Applications/Google Chrome.app` is detected automatically.

---

## Measuring a Production Build (Recommended)

For numbers closest to real user experience, measure the **Vite preview server** (serves the built bundle, no HMR overhead):

```bash
# In r-mos-frontend:
npm run build          # generates dist/
npm run preview        # starts http://localhost:4173 by default

# In a second terminal:
BASE_URL=http://localhost:4173 npm run perf:lighthouse
```

> Vite preview defaults to port **4173**. Dev server (`npm run dev`) defaults to **5173**.

---

## Environment Variables

| Variable     | Default                  | Description |
|--------------|--------------------------|-------------|
| `BASE_URL`   | `http://localhost:5173`  | Origin of the running app |
| `AUTH_TOKEN` | *(empty)*                | JWT access token for auth-protected routes |

---

## Measuring Auth-Protected Routes

Most R-MOS pages require a logged-in session. Obtain a token first:

```bash
# Option A — curl (replace with real credentials)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@example.com","password":"your_password"}' \
  | python3 -m json.tool | grep access_token | awk -F'"' '{print $4}')

# Option B — from browser DevTools
# Open DevTools → Application → Local Storage → http://localhost:4173
# Copy the value of key: rmos_access_token

# Then run with token
BASE_URL=http://localhost:4173 AUTH_TOKEN="$TOKEN" npm run perf:lighthouse
```

When `AUTH_TOKEN` is set, the script:
- Sets the `Authorization: Bearer <token>` header so API calls within the Lighthouse run are authenticated.
- Sets `disableStorageReset: true` to avoid Lighthouse clearing localStorage between audits.

> **Note:** Lighthouse measures the first-paint of the cold page load. The app reads the token from localStorage on init (`authStore.initFromStorage`). Because Lighthouse launches a fresh Chrome profile, localStorage is empty unless the app picks up the token from the Authorization header or falls back to the login redirect. For the most accurate protected-route FCP/LCP, use a running backend so the app can complete auth and render the real page — otherwise the redirect to `/login` will be what Lighthouse measures.

**Public-only measurement** (no backend needed):

```bash
# Measures only /login and /register — no AUTH_TOKEN required
npm run perf:lighthouse
```

---

## How to Run

```bash
# Minimal (public pages only, dev server)
npm run perf:lighthouse

# Full (all routes, preview build, with auth)
npm run build && npm run preview &
BASE_URL=http://localhost:4173 AUTH_TOKEN="$TOKEN" npm run perf:lighthouse
```

---

## Output

### Raw JSON

Saved to `scripts/perf/out/<route>-<timestamp>.json` (gitignored). Each file is the full Lighthouse result object (LHR) — open with [Lighthouse Viewer](https://googlechrome.github.io/lighthouse/viewer/) or inspect `lhr.audits.*`.

### Markdown Table (stdout)

Printed to stdout after all routes are measured:

```
| Route      | Label          | Score | FCP    | LCP     | TBT   | CLS  | TTI    |
|------------|----------------|-------|--------|---------|-------|------|--------|
| `/login`   | Login Page     | 98    | 420 ms | 430 ms  | 0 ms  | 0    | 432 ms |
| `/dashboard` | Student Dashboard | 85 | 820 ms | 1100 ms | 45 ms | 0.01 | 1200 ms |
```

Paste this table into `docs/superpowers/plans/phase4-baseline.md`.

---

## Metrics Reference

| Metric | Full Name | Good | Needs Improvement | Poor |
|--------|-----------|------|-------------------|----|
| FCP | First Contentful Paint | < 1.8 s | 1.8–3 s | > 3 s |
| LCP | Largest Contentful Paint | < 2.5 s | 2.5–4 s | > 4 s |
| TBT | Total Blocking Time | < 200 ms | 200–600 ms | > 600 ms |
| CLS | Cumulative Layout Shift | < 0.1 | 0.1–0.25 | > 0.25 |
| TTI | Time to Interactive | < 3.8 s | 3.8–7.3 s | > 7.3 s |

---

## Troubleshooting

**"Missing required packages"** — Run `npm i -D lighthouse chrome-launcher`.

**"Failed to launch Chrome"** — Install Chrome/Chromium. On Linux: `apt install chromium-browser` or `snap install chromium`.

**All protected routes skipped** — Set `AUTH_TOKEN` (see above).

**Numbers vary between runs** — Run 3× and take the median. Lighthouse desktop preset disables network/CPU throttling; vary if the machine is under load.
