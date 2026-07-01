/**
 * ws-probe.mjs — WebSocket 遥测时延/吞吐探针
 *
 * 仅用于性能基线测量，不修改任何产品代码。
 *
 * Usage:
 *   WS_URL=ws://localhost:8000/ws/robot/status \
 *   WS_DURATION_SEC=20 \
 *   node scripts/perf/ws-probe.mjs
 *
 * Prerequisites (on demand, not in package.json):
 *   npm i -D ws
 */

// ---------------------------------------------------------------------------
// 1. Guard: detect missing `ws` package without a stack trace
// ---------------------------------------------------------------------------
let WebSocket;
try {
  ({ WebSocket } = await import('ws'));
} catch {
  process.stderr.write(
    '[ws-probe] ERROR: the `ws` package is not installed.\n' +
    '  Run:  npm i -D ws\n' +
    '  Then: npm run perf:ws\n'
  );
  process.exit(1);
}

// ---------------------------------------------------------------------------
// 2. Configuration
// ---------------------------------------------------------------------------
const WS_URL         = process.env.WS_URL          || 'ws://localhost:8000/ws/robot/status';
const DURATION_SEC   = Number(process.env.WS_DURATION_SEC ?? 20);
const HZ_TARGET      = 200;       // ms — expected inter-arrival interval at 5 Hz
const HZ_TOLERANCE   = 0.20;      // ±20 % → [160 ms, 240 ms] counts as on-target

// ---------------------------------------------------------------------------
// 3. State
// ---------------------------------------------------------------------------
const arrivalTimes   = [];   // epoch ms of each telemetry message
const pingTimes      = new Map(); // pingSeq → send epoch ms
const rttSamples     = [];   // ms
let   disconnectCount = 0;
let   pingSeq         = 0;

// ---------------------------------------------------------------------------
// 4. Connect
// ---------------------------------------------------------------------------
process.stdout.write(`[ws-probe] Connecting to ${WS_URL} for ${DURATION_SEC}s …\n`);

let ws;
try {
  ws = new WebSocket(WS_URL);
} catch (err) {
  process.stderr.write(`[ws-probe] ERROR: cannot create WebSocket — ${err.message}\n`);
  process.exit(1);
}

// Connection refused / DNS failure arrives as an 'error' event
ws.on('error', (err) => {
  const msg = err.code === 'ECONNREFUSED'
    ? `Connection refused — is the backend running at ${WS_URL}?`
    : err.message;
  process.stderr.write(`[ws-probe] ERROR: ${msg}\n`);
  // process.exit happens in the 'close' handler that follows an error
});

ws.on('close', () => {
  disconnectCount += 1;
  // If we closed before collecting any data the connection itself failed
  if (arrivalTimes.length === 0 && disconnectCount === 1) {
    process.stderr.write('[ws-probe] Connection closed with no telemetry received. Exiting.\n');
    process.exit(1);
  }
});

ws.on('open', () => {
  process.stdout.write('[ws-probe] Connected.\n');
});

// ---------------------------------------------------------------------------
// 5. Message handler
// ---------------------------------------------------------------------------
ws.on('message', (raw) => {
  const now = Date.now();
  let msg;
  try {
    msg = JSON.parse(raw.toString());
  } catch {
    return; // ignore malformed frames
  }

  if (msg.type === 'ping') {
    // Mirror the real client: reply pong immediately and record RTT basis
    const seq = ++pingSeq;
    pingTimes.set(seq, now);
    ws.send(JSON.stringify({ type: 'pong' }));
    // Measure RTT as time from sending pong to next server ping (approximate)
    // — because the server doesn't echo pong, we record the round-trip from
    //   "we sent pong" to "server sent the NEXT ping", i.e. one full ping cycle.
    // We store the send time; the next ping arrival is compared below.
    if (pingTimes.size > 1) {
      const seqArr = [...pingTimes.keys()];
      const prev   = seqArr[seqArr.length - 2];
      const prevTs = pingTimes.get(prev);
      if (prevTs !== undefined) {
        rttSamples.push(now - prevTs);
        pingTimes.delete(prev);
      }
    }
    return;
  }

  if (msg.type === 'telemetry') {
    arrivalTimes.push(now);
  }
});

// ---------------------------------------------------------------------------
// 6. Run for DURATION_SEC then report
// ---------------------------------------------------------------------------
await new Promise((resolve) => setTimeout(resolve, DURATION_SEC * 1000));

// Graceful close — subtract the subsequent disconnect from our counter
ws.removeAllListeners('close');
ws.close(1000, 'probe done');

// ---------------------------------------------------------------------------
// 7. Compute statistics
// ---------------------------------------------------------------------------
const n = arrivalTimes.length;

if (n < 2) {
  process.stderr.write(
    `[ws-probe] Not enough data (${n} message(s) received). ` +
    'Is the backend running and sending telemetry?\n'
  );
  process.exit(1);
}

// Inter-arrival intervals (ms)
const intervals = [];
for (let i = 1; i < n; i++) {
  intervals.push(arrivalTimes[i] - arrivalTimes[i - 1]);
}

intervals.sort((a, b) => a - b);

const mean = intervals.reduce((s, v) => s + v, 0) / intervals.length;

const p50  = percentile(intervals, 50);
const p95  = percentile(intervals, 95);

const lo   = HZ_TARGET * (1 - HZ_TOLERANCE);  // 160 ms
const hi   = HZ_TARGET * (1 + HZ_TOLERANCE);  // 240 ms
const onTarget = intervals.filter((v) => v >= lo && v <= hi).length;
const hz5Rate  = ((onTarget / intervals.length) * 100).toFixed(1);

// Approximate throughput
const durationMs = arrivalTimes[n - 1] - arrivalTimes[0];
const actualHz   = durationMs > 0 ? ((n - 1) / (durationMs / 1000)).toFixed(2) : 'N/A';

// Ping→pong RTT (inter-ping cycle as proxy)
const rttMean = rttSamples.length > 0
  ? (rttSamples.reduce((s, v) => s + v, 0) / rttSamples.length).toFixed(1)
  : 'N/A';

// ---------------------------------------------------------------------------
// 8. Output
// ---------------------------------------------------------------------------
process.stdout.write('\n');
process.stdout.write('## WebSocket Telemetry Probe Results\n\n');

process.stdout.write(
  '| Metric                          | Value         |\n' +
  '|---------------------------------|---------------|\n' +
  `| Duration (s)                    | ${DURATION_SEC}            |\n` +
  `| Total telemetry messages        | ${n}            |\n` +
  `| Actual throughput (Hz)          | ${actualHz}         |\n` +
  `| Inter-arrival mean (ms)         | ${mean.toFixed(1)}         |\n` +
  `| Inter-arrival P50 (ms)          | ${p50.toFixed(1)}         |\n` +
  `| Inter-arrival P95 (ms)          | ${p95.toFixed(1)}         |\n` +
  `| 5 Hz achievement rate (%)       | ${hz5Rate}          |\n` +
  `| 5 Hz band [${lo}–${hi} ms]        | ${onTarget}/${intervals.length} intervals |\n` +
  `| Ping→pong cycle RTT mean (ms)   | ${rttMean}          |\n` +
  `| Disconnect count                | ${disconnectCount}            |\n`
);

process.stdout.write('\n');
process.stdout.write(
  `> **5 Hz rate** = % of consecutive message intervals that fall within ` +
  `${lo}–${hi} ms (±${HZ_TOLERANCE * 100}% of the 200 ms target).\n`
);
process.stdout.write('\n');

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------
function percentile(sorted, p) {
  const idx = (p / 100) * (sorted.length - 1);
  const lo2 = Math.floor(idx);
  const hi2 = Math.ceil(idx);
  if (lo2 === hi2) return sorted[lo2];
  return sorted[lo2] + (sorted[hi2] - sorted[lo2]) * (idx - lo2);
}
