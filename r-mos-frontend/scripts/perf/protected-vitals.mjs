/**
 * Protected-route Web Vitals via chrome-launcher + CDP.
 *
 * 修复 lighthouse.mjs 的认证缺陷：该脚本用 extraHeaders Bearer 注入，只影响
 * 网络请求，对客户端 localStorage 路由守卫无效 → 受保护路由全部重定向 /login，
 * 测到的是登录页。本脚本在页面 JS 运行前用 Page.addScriptToEvaluateOnNewDocument
 * 注入 authStore 需要的全部 localStorage key，守卫据此认定已登录，从而测到真实页面。
 *
 * 用法：
 *   AUTH_JSON=/tmp/perf-auth.json BASE_URL=http://localhost:4173 \
 *   ROUTES=/workbench/teaching,/maintenance,/monitor node scripts/perf/protected-vitals.mjs
 */
import { createRequire } from 'module'
import fs from 'fs'

const require = createRequire(import.meta.url)
const chromeLauncher = require('chrome-launcher')
const CDP = require('chrome-remote-interface')

const BASE_URL = process.env.BASE_URL || 'http://localhost:4173'
const AUTH = JSON.parse(fs.readFileSync(process.env.AUTH_JSON || '/tmp/perf-auth.json', 'utf8'))
const ROUTES = (process.env.ROUTES || '/workbench/teaching,/maintenance,/monitor').split(',')

// 页面加载前注入的脚本：铺满 authStore 需要的 localStorage key
const injectScript = `(function(){try{const a=${JSON.stringify(AUTH)};for(const k in a){localStorage.setItem(k,a[k]);}}catch(e){}})();`

async function measure(client, url) {
  const { Page, Runtime, Performance } = client
  await Page.enable()
  await Runtime.enable()
  await Performance.enable()
  // 关键：页面 JS 运行前注入认证 localStorage
  await Page.addScriptToEvaluateOnNewDocument({ source: injectScript })

  const t0 = Date.now()
  await Page.navigate({ url })
  await Page.loadEventFired()
  // 等 SPA 渲染 + 潜在重定向稳定
  await new Promise((r) => setTimeout(r, 3500))

  const metrics = await Runtime.evaluate({
    expression: `(() => {
      const nav = performance.getEntriesByType('navigation')[0] || {};
      const paints = performance.getEntriesByType('paint');
      const fcp = (paints.find(p=>p.name==='first-contentful-paint')||{}).startTime;
      let lcp = 0;
      try { const l = performance.getEntriesByType('largest-contentful-paint'); if(l.length) lcp = l[l.length-1].startTime; } catch(e){}
      return JSON.stringify({
        finalUrl: location.pathname,
        domNodes: document.querySelectorAll('*').length,
        fcp: Math.round(fcp||0),
        domContentLoaded: Math.round(nav.domContentLoadedEventEnd||0),
        loadEvent: Math.round(nav.loadEventEnd||0),
        resources: performance.getEntriesByType('resource').length,
        transferKB: Math.round(performance.getEntriesByType('resource').reduce((s,r)=>s+(r.transferSize||0),0)/1024)
      });
    })()`,
    returnByValue: true,
  })
  const m = JSON.parse(metrics.result.value)
  m.wallMs = Date.now() - t0
  return m
}

;(async () => {
  const chrome = await chromeLauncher.launch({
    chromeFlags: ['--headless=new', '--disable-gpu', '--no-sandbox'],
  })
  const rows = []
  try {
    for (const route of ROUTES) {
      const client = await CDP({ port: chrome.port })
      try {
        const m = await measure(client, `${BASE_URL}${route}`)
        const redirected = m.finalUrl.startsWith('/login') && route !== '/login'
        rows.push({ route, ...m, redirected })
        console.log(
          `${route.padEnd(24)} final=${m.finalUrl.padEnd(20)} ${redirected ? 'REDIRECTED!' : 'OK'} ` +
            `dom=${m.domNodes} fcp=${m.fcp}ms dcl=${m.domContentLoaded}ms load=${m.loadEvent}ms ` +
            `res=${m.resources} ${m.transferKB}KB`,
        )
      } finally {
        await client.close()
      }
    }
  } finally {
    await chrome.kill()
  }

  console.log('\n## Protected-route Vitals\n')
  console.log('| 路由 | 最终URL | DOM节点 | FCP(ms) | DCL(ms) | Load(ms) | 请求数 | 传输(KB) | 有效? |')
  console.log('|------|---------|---------|---------|---------|----------|--------|----------|-------|')
  for (const r of rows) {
    console.log(
      `| ${r.route} | ${r.finalUrl} | ${r.domNodes} | ${r.fcp} | ${r.domContentLoaded} | ${r.loadEvent} | ${r.resources} | ${r.transferKB} | ${r.redirected ? '❌重定向' : '✅'} |`,
    )
  }
})()
