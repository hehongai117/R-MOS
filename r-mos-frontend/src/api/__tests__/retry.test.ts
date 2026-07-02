/**
 * retry.test.ts — Phase 4 Task A2
 * TDD: RED → GREEN
 * Tests for shouldRetry, backoffDelay, and installRetry.
 * No axios-mock-adapter dep; hand-mock via a custom AxiosAdapter.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import axios, {
  AxiosError,
  CanceledError,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { backoffDelay, installRetry, shouldRetry } from '../retry'
import type { RetryOptions } from '../retry'

// ---------------------------------------------------------------------------
// Minimal hand-rolled mock adapter
// ---------------------------------------------------------------------------
type MockSpec =
  | { type: 'success'; status?: number; data?: unknown }
  | { type: 'http-error'; status: number }
  | { type: 'network-error' }

function makeAdapter(specs: MockSpec[]): { adapter: AxiosAdapter; calls: () => number } {
  let calls = 0
  const queue = [...specs]

  const adapter: AxiosAdapter = async (config: InternalAxiosRequestConfig) => {
    calls++
    const spec = queue.shift()
    if (!spec) throw new Error('Mock adapter: no more specs')

    if (spec.type === 'success') {
      return {
        status: spec.status ?? 200,
        data: spec.data ?? {},
        headers: {},
        config,
        statusText: 'OK',
      } as AxiosResponse
    }

    if (spec.type === 'network-error') {
      throw new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {}, undefined)
    }

    // http-error
    const res: AxiosResponse = {
      status: spec.status,
      data: { message: `Error ${spec.status}` },
      headers: {},
      config,
      statusText: String(spec.status),
    }
    throw new AxiosError(
      `Request failed with status code ${spec.status}`,
      AxiosError.ERR_BAD_RESPONSE,
      config,
      {},
      res,
    )
  }

  return { adapter, calls: () => calls }
}

// ---------------------------------------------------------------------------
// shouldRetry unit tests
// ---------------------------------------------------------------------------
describe('shouldRetry', () => {
  const makeErr = (
    method: string,
    status?: number,
    code?: string,
  ): AxiosError => {
    const config = { method, url: '/test' } as InternalAxiosRequestConfig
    const response = status
      ? ({ status, data: {}, headers: {}, config, statusText: String(status) } as AxiosResponse)
      : undefined
    return new AxiosError('err', code ?? AxiosError.ERR_NETWORK, config, {}, response)
  }

  it('returns true for GET with network error at attempt 0', () => {
    expect(shouldRetry(makeErr('GET'), 0, {})).toBe(true)
  })

  it('returns true for HEAD with 502', () => {
    expect(shouldRetry(makeErr('HEAD', 502), 0, {})).toBe(true)
  })

  it('returns true for OPTIONS with 503', () => {
    expect(shouldRetry(makeErr('OPTIONS', 503), 0, {})).toBe(true)
  })

  it('returns true for GET with 504', () => {
    expect(shouldRetry(makeErr('GET', 504), 0, {})).toBe(true)
  })

  it('returns false for POST with 503 by default', () => {
    expect(shouldRetry(makeErr('POST', 503), 0, {})).toBe(false)
  })

  it('returns false for 401 (must not consume 401)', () => {
    expect(shouldRetry(makeErr('GET', 401), 0, {})).toBe(false)
  })

  it('returns false for 500 (not in default statuses)', () => {
    expect(shouldRetry(makeErr('GET', 500), 0, {})).toBe(false)
  })

  it('returns false when attempt >= maxRetries (default 2)', () => {
    expect(shouldRetry(makeErr('GET'), 2, {})).toBe(false)
    expect(shouldRetry(makeErr('GET'), 3, {})).toBe(false)
  })

  it('returns false for cancel errors regardless of method', () => {
    // axios 1.18.x 的 CanceledError 构造签名为 (message, config, request)，无 code 位；
    // shouldRetry 靠 axios.isCancel()(__CANCEL__ 标记)判定，仅 message 即可。
    const cancelErr = new CanceledError('cancelled', {
      method: 'get',
    } as InternalAxiosRequestConfig)
    expect(shouldRetry(cancelErr as AxiosError, 0, {})).toBe(false)
  })

  it('returns true for POST when config.retry===true', () => {
    const config = { method: 'post', url: '/test', retry: true } as InternalAxiosRequestConfig & {
      retry?: boolean
    }
    const err = new AxiosError('err', AxiosError.ERR_NETWORK, config, {})
    expect(shouldRetry(err, 0, {})).toBe(true)
  })

  it('respects custom maxRetries', () => {
    const opts: RetryOptions = { maxRetries: 5 }
    expect(shouldRetry(makeErr('GET'), 4, opts)).toBe(true)
    expect(shouldRetry(makeErr('GET'), 5, opts)).toBe(false)
  })

  it('respects custom methods list', () => {
    const opts: RetryOptions = { methods: ['DELETE'] }
    expect(shouldRetry(makeErr('DELETE'), 0, opts)).toBe(true)
    expect(shouldRetry(makeErr('GET'), 0, opts)).toBe(false)
  })

  it('respects custom statuses list', () => {
    const opts: RetryOptions = { statuses: [500, 502] }
    expect(shouldRetry(makeErr('GET', 500), 0, opts)).toBe(true)
    expect(shouldRetry(makeErr('GET', 503), 0, opts)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// backoffDelay unit tests
// ---------------------------------------------------------------------------
describe('backoffDelay', () => {
  it('is bounded by cap (default 4000)', () => {
    for (let i = 0; i < 50; i++) {
      expect(backoffDelay(20)).toBeLessThanOrEqual(4000)
    }
  })

  it('is non-negative', () => {
    for (let i = 0; i < 20; i++) {
      expect(backoffDelay(0)).toBeGreaterThanOrEqual(0)
    }
  })

  it('is monotonically increasing (zero jitter via Math.random mock)', () => {
    const spy = vi.spyOn(Math, 'random').mockReturnValue(0)
    try {
      const d0 = backoffDelay(0)
      const d1 = backoffDelay(1)
      const d2 = backoffDelay(2)
      expect(d1).toBeGreaterThan(d0)
      expect(d2).toBeGreaterThan(d1)
    } finally {
      spy.mockRestore()
    }
  })

  it('respects a custom base and cap', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0)
    try {
      expect(backoffDelay(0, 100, 500)).toBe(100)
      expect(backoffDelay(3, 100, 500)).toBe(500) // capped
    } finally {
      vi.restoreAllMocks()
    }
  })
})

// ---------------------------------------------------------------------------
// installRetry integration tests (using hand-rolled mock adapter)
// ---------------------------------------------------------------------------
describe('installRetry integration', () => {
  const noDelay: RetryOptions = { maxRetries: 2, delayFn: () => 0 }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('(a) retries idempotent GET on 503 then succeeds', async () => {
    const { adapter, calls } = makeAdapter([
      { type: 'http-error', status: 503 },
      { type: 'http-error', status: 503 },
      { type: 'success', data: { ok: true } },
    ])
    const client = axios.create({ adapter })
    installRetry(client, noDelay)

    const res = await client.get('/test')
    expect(res.data).toEqual({ ok: true })
    expect(calls()).toBe(3) // initial + 2 retries
  })

  it('(b) rejects after exceeding maxRetries with correct call count', async () => {
    const { adapter, calls } = makeAdapter([
      { type: 'http-error', status: 503 },
      { type: 'http-error', status: 503 },
      { type: 'http-error', status: 503 },
    ])
    const client = axios.create({ adapter })
    installRetry(client, noDelay)

    const err = await client.get('/test').catch((e) => e)
    expect(err).toBeInstanceOf(AxiosError)
    expect(err.response?.status).toBe(503)
    expect(calls()).toBe(3) // initial + 2 retries = maxRetries+1
  })

  it('(c) does NOT retry POST by default', async () => {
    const { adapter, calls } = makeAdapter([{ type: 'http-error', status: 503 }])
    const client = axios.create({ adapter })
    installRetry(client, noDelay)

    await expect(client.post('/test', {})).rejects.toBeInstanceOf(AxiosError)
    expect(calls()).toBe(1) // no retry
  })

  it('(d) does NOT consume 401 — error still rejects with status 401', async () => {
    const { adapter, calls } = makeAdapter([{ type: 'http-error', status: 401 }])
    const client = axios.create({ adapter })
    installRetry(client, noDelay)

    const err = await client.get('/test').catch((e) => e)
    expect(err).toBeInstanceOf(AxiosError)
    expect(err.response?.status).toBe(401)
    expect(calls()).toBe(1) // no retry: 401 must pass through
  })

  it('retries GET on network error (no response)', async () => {
    const { adapter, calls } = makeAdapter([
      { type: 'network-error' },
      { type: 'success', data: { recovered: true } },
    ])
    const client = axios.create({ adapter })
    installRetry(client, noDelay)

    const res = await client.get('/test')
    expect(res.data).toEqual({ recovered: true })
    expect(calls()).toBe(2)
  })

  it('does not retry 500 (not in default statuses)', async () => {
    const { adapter, calls } = makeAdapter([{ type: 'http-error', status: 500 }])
    const client = axios.create({ adapter })
    installRetry(client, noDelay)

    await expect(client.get('/test')).rejects.toMatchObject({ response: { status: 500 } })
    expect(calls()).toBe(1)
  })

  it('POST with config.retry===true is retried', async () => {
    const { adapter, calls } = makeAdapter([
      { type: 'http-error', status: 502 },
      { type: 'success', data: { posted: true } },
    ])
    const client = axios.create({ adapter })
    installRetry(client, noDelay)

    const res = await client.post('/test', {}, { retry: true } as object)
    expect(res.data).toEqual({ posted: true })
    expect(calls()).toBe(2)
  })

  it('calls delayFn with the current attempt index', async () => {
    const delayFn = vi.fn().mockReturnValue(0)
    const { adapter } = makeAdapter([
      { type: 'http-error', status: 503 },
      { type: 'success' },
    ])
    const client = axios.create({ adapter })
    installRetry(client, { maxRetries: 2, delayFn })

    await client.get('/test')
    expect(delayFn).toHaveBeenCalledWith(0)
  })

  it('uses actual backoffDelay when delayFn not provided (smoke test)', async () => {
    // Just verifying installRetry works without an explicit delayFn override.
    // Use maxRetries=0 so no delay is ever computed.
    const { adapter, calls } = makeAdapter([{ type: 'http-error', status: 503 }])
    const client = axios.create({ adapter })
    installRetry(client, { maxRetries: 0 })

    await expect(client.get('/test')).rejects.toBeInstanceOf(AxiosError)
    expect(calls()).toBe(1)
  })
})
