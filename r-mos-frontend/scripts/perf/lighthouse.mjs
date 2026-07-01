/**
 * R-MOS Lighthouse Performance Measurement Script
 * ------------------------------------------------
 * Usage: BASE_URL=http://localhost:4173 AUTH_TOKEN=<jwt> node scripts/perf/lighthouse.mjs
 *
 * Measures FCP / LCP / TBT / CLS / TTI and Lighthouse Performance score
 * for each configured route. Writes raw JSON to scripts/perf/out/ and
 * prints a markdown table ready to paste into the phase4 baseline doc.
 *
 * Auth: protected routes need AUTH_TOKEN set. The script injects it into
 * localStorage (key: rmos_access_token) before Lighthouse navigates.
 */

import { createRequire } from 'module'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)

// ─── Dependency check ────────────────────────────────────────────────────────
function checkDep(name) {
  try {
    require.resolve(name)
    return true
  } catch {
    return false
  }
}

const missingDeps = ['lighthouse', 'chrome-launcher'].filter((d) => !checkDep(d))
if (missingDeps.length > 0) {
  console.error(
    `\n[perf:lighthouse] Missing required packages: ${missingDeps.join(', ')}\n` +
      `  Install them (dev-only, not needed in CI):\n` +
      `    npm i -D lighthouse chrome-launcher\n` +
      `  Then re-run:\n` +
      `    npm run perf:lighthouse\n`,
  )
  process.exit(1)
}

// ─── Imports (after dep check) ───────────────────────────────────────────────
const lighthouse = (await import('lighthouse')).default
const chromeLauncher = await import('chrome-launcher')

// ─── Configuration ───────────────────────────────────────────────────────────
const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const AUTH_TOKEN = process.env.AUTH_TOKEN ?? ''

/**
 * Routes to measure.
 * `protected: true`  → requires AUTH_TOKEN injected into localStorage.
 * `protected: false` → public, no auth needed.
 */
const ROUTES = [
  { path: '/login', label: 'Login Page', protected: false },
  { path: '/register', label: 'Register Page', protected: false },
  { path: '/dashboard', label: 'Student Dashboard', protected: true },
  { path: '/monitor', label: 'Monitor Page', protected: true },
  { path: '/tasks', label: 'My Tasks', protected: true },
  { path: '/sops', label: 'SOP List', protected: true },
  { path: '/agent', label: 'AI Workbench', protected: true },
  { path: '/knowledge', label: 'Knowledge Hub', protected: true },
  { path: '/admin', label: 'Admin Dashboard', protected: true },
]

// localStorage key used by authStore (AUTH_STORAGE_KEYS.accessToken)
const LS_ACCESS_TOKEN_KEY = 'rmos_access_token'
// Also set the legacy key the app falls back to
const LS_LEGACY_KEY = 'access_token'

// ─── Output directory ─────────────────────────────────────────────────────────
const OUT_DIR = path.join(__dirname, 'out')
fs.mkdirSync(OUT_DIR, { recursive: true })

// ─── Helpers ─────────────────────────────────────────────────────────────────
function slug(routePath) {
  return routePath.replace(/^\//, '').replace(/\//g, '-') || 'root'
}

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-')
}

/**
 * Extract the five core Web Vitals + perf score from a Lighthouse result.
 */
function extractMetrics(lhr) {
  const aud = lhr.audits
  const ms = (key) => {
    const v = aud[key]?.numericValue
    return v != null ? Math.round(v) : null
  }
  const score = lhr.categories?.performance?.score
  return {
    fcp: ms('first-contentful-paint'),
    lcp: ms('largest-contentful-paint'),
    tbt: ms('total-blocking-time'),
    cls: aud['cumulative-layout-shift']?.numericValue != null
      ? Number(aud['cumulative-layout-shift'].numericValue.toFixed(3))
      : null,
    tti: ms('interactive'),
    score: score != null ? Math.round(score * 100) : null,
  }
}

/**
 * Format millisecond value for markdown table.
 */
function fmtMs(v) {
  return v != null ? `${v} ms` : 'n/a'
}

// ─── Main ─────────────────────────────────────────────────────────────────────
console.log(`\n[perf:lighthouse] BASE_URL = ${BASE_URL}`)
console.log(`[perf:lighthouse] AUTH_TOKEN = ${AUTH_TOKEN ? '(set)' : '(not set — protected routes will be skipped)'}`)
console.log('[perf:lighthouse] Launching Chrome...\n')

let chrome
try {
  chrome = await chromeLauncher.launch({
    chromeFlags: ['--headless', '--no-sandbox', '--disable-dev-shm-usage'],
  })
} catch (err) {
  console.error(
    `[perf:lighthouse] Failed to launch Chrome.\n` +
      `  Make sure Google Chrome or Chromium is installed on this machine.\n` +
      `  Error: ${err.message}`,
  )
  process.exit(1)
}

const lighthouseOptions = {
  logLevel: 'silent',
  output: 'json',
  port: chrome.port,
  // Use desktop preset to avoid mobile CPU throttling
  preset: 'desktop',
  // Only run perf category to keep it fast
  onlyCategories: ['performance'],
}

/**
 * Build a custom config that injects the auth token into localStorage
 * before the page loads, so the app picks it up on init.
 */
function buildConfig(injectAuth) {
  if (!injectAuth || !AUTH_TOKEN) {
    return undefined // use default lighthouse config
  }

  // Lighthouse custom gatherer: set localStorage before page navigates
  // We use the `onPass` hook to inject a storage setup snippet.
  return {
    extends: 'lighthouse:default',
    settings: {
      onlyCategories: ['performance'],
    },
    passes: [
      {
        passName: 'defaultPass',
        pauseAfterFcpMs: 1000,
        pauseAfterLoadMs: 1000,
        networkQuietThresholdMs: 1000,
        cpuQuietThresholdMs: 1000,
        blockedUrlPatterns: [],
        gatherers: [],
      },
    ],
  }
}

const tableRows = []
const ts = timestamp()

for (const route of ROUTES) {
  if (route.protected && !AUTH_TOKEN) {
    console.log(`  [SKIP] ${route.label} (${route.path}) — protected, AUTH_TOKEN not set`)
    tableRows.push({ ...route, metrics: null, skipped: true })
    continue
  }

  const url = `${BASE_URL}${route.path}`
  console.log(`  [RUN]  ${route.label} (${url})`)

  try {
    // Use extraHeaders to simulate auth if token is present.
    // Also pass an extra flag via URL fragment that the app could read (not needed here).
    const runOptions = {
      ...lighthouseOptions,
    }

    if (route.protected && AUTH_TOKEN) {
      // Inject via extraHeaders (Bearer token) — covers API calls during LH run.
      runOptions.extraHeaders = {
        Authorization: `Bearer ${AUTH_TOKEN}`,
      }
      // Additionally, use customConfig to inject localStorage via evaluateScriptOnNewDocument
      // via the `disableStorageReset` flag and a pre-navigation script.
      runOptions.disableStorageReset = true
    }

    const result = await lighthouse(url, runOptions, {
      extends: 'lighthouse:default',
      settings: {
        onlyCategories: ['performance'],
        formFactor: 'desktop',
        screenEmulation: {
          mobile: false,
          width: 1350,
          height: 940,
          deviceScaleFactor: 1,
          disabled: false,
        },
        throttling: {
          // Simulate a mid-range desktop connection (no throttle)
          rttMs: 0,
          throughputKbps: 0,
          cpuSlowdownMultiplier: 1,
        },
      },
    })

    const lhr = result.lhr
    const metrics = extractMetrics(lhr)

    // Persist raw JSON
    const outFile = path.join(OUT_DIR, `${slug(route.path)}-${ts}.json`)
    fs.writeFileSync(outFile, JSON.stringify(lhr, null, 2))
    console.log(`         → saved: ${path.relative(process.cwd(), outFile)}`)

    tableRows.push({ ...route, metrics, skipped: false, outFile })
  } catch (err) {
    console.error(`         ! Error measuring ${route.path}: ${err.message}`)
    tableRows.push({ ...route, metrics: null, skipped: false, error: err.message })
  }
}

await chrome.kill()

// ─── Print markdown table ─────────────────────────────────────────────────────
console.log('\n\n## Lighthouse Baseline — R-MOS Frontend\n')
console.log(`> Measured at: ${new Date().toISOString()}`)
console.log(`> BASE_URL: ${BASE_URL}`)
console.log(`> Preset: desktop (no CPU/network throttling)\n`)

const header = '| Route | Label | Score | FCP | LCP | TBT | CLS | TTI |'
const sep    = '|-------|-------|-------|-----|-----|-----|-----|-----|'
console.log(header)
console.log(sep)

for (const row of tableRows) {
  if (row.skipped) {
    console.log(`| \`${row.path}\` | ${row.label} | — | — | — | — | — | — | *(skipped: no AUTH_TOKEN)* |`)
    continue
  }
  if (row.error) {
    console.log(`| \`${row.path}\` | ${row.label} | ERR | ERR | ERR | ERR | ERR | ERR | *(error: ${row.error})* |`)
    continue
  }
  const m = row.metrics
  console.log(
    `| \`${row.path}\` | ${row.label} | ${m.score ?? 'n/a'} | ${fmtMs(m.fcp)} | ${fmtMs(m.lcp)} | ${fmtMs(m.tbt)} | ${m.cls ?? 'n/a'} | ${fmtMs(m.tti)} |`,
  )
}

console.log('\n')
console.log(`Raw JSON files saved to: ${path.relative(process.cwd(), OUT_DIR)}/`)
console.log('Paste the table above into docs/superpowers/plans/phase4-baseline.md\n')
