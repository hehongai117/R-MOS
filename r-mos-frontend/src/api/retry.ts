/**
 * retry.ts — Phase 4 Task A2
 * Transient-failure retry with exponential backoff for axios, scoped to
 * idempotent requests.  Orthogonal to the existing 401 auth-refresh flow.
 */
import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RetryOptions {
  /** Maximum number of retry attempts (default: 2). */
  maxRetries?: number
  /** HTTP methods that are eligible for retry (default: GET, HEAD, OPTIONS). */
  methods?: string[]
  /** HTTP status codes that trigger a retry (default: 502, 503, 504). */
  statuses?: number[]
  /**
   * Override the delay function for testing without real sleeps.
   * Receives the zero-based attempt index; returns ms to wait.
   * Defaults to backoffDelay(attempt).
   */
  delayFn?: (attempt: number) => number
}

/** Private extension of InternalAxiosRequestConfig tracked by the interceptor. */
interface RetryConfig extends InternalAxiosRequestConfig {
  /** Number of retries already performed (undefined = 0 on first attempt). */
  _retryAttempt?: number
  /** Opt-in flag: set to true on the request to force retry even for non-idempotent methods. */
  retry?: boolean
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_MAX_RETRIES = 2
const DEFAULT_METHODS = ['GET', 'HEAD', 'OPTIONS']
const DEFAULT_STATUSES = [502, 503, 504]

// ---------------------------------------------------------------------------
// Pure functions
// ---------------------------------------------------------------------------

/**
 * Decide whether the failed request should be retried.
 *
 * Returns true when ALL of the following hold:
 *  - attempt < maxRetries
 *  - error is not a cancellation
 *  - the request method is idempotent (GET/HEAD/OPTIONS) OR config.retry===true
 *  - error has no response (network / timeout) OR response.status ∈ {502,503,504}
 *    (401 has a response with status 401, which is NOT in the default statuses
 *    list and therefore naturally falls through to the existing refresh logic.)
 */
export function shouldRetry(
  error: AxiosError,
  attempt: number,
  opts: RetryOptions,
): boolean {
  const maxRetries = opts.maxRetries ?? DEFAULT_MAX_RETRIES
  const methods = opts.methods ?? DEFAULT_METHODS
  const statuses = opts.statuses ?? DEFAULT_STATUSES

  if (attempt >= maxRetries) return false
  if (axios.isCancel(error)) return false

  const config = error.config as RetryConfig | undefined
  if (!config) return false

  const method = (config.method ?? 'GET').toUpperCase()
  const isIdempotent = methods.includes(method) || config.retry === true
  if (!isIdempotent) return false

  // Network / timeout error — no response object.
  if (!error.response) return true

  // Server-side transient error.
  return statuses.includes(error.response.status)
}

/**
 * Compute the next backoff delay in milliseconds.
 * Formula: min(base * 2^attempt + jitter, cap)  where jitter ∈ [0, base).
 *
 * @param attempt  Zero-based retry index.
 * @param base     Base delay in ms (default 300).
 * @param cap      Maximum delay in ms (default 4000).
 */
export function backoffDelay(attempt: number, base = 300, cap = 4000): number {
  const exp = base * Math.pow(2, attempt)
  const jitter = Math.random() * base
  return Math.min(exp + jitter, cap)
}

// ---------------------------------------------------------------------------
// Installer
// ---------------------------------------------------------------------------

/**
 * Install a retry response interceptor on `client`.
 *
 * Interceptor ordering note (axios FIFO for response interceptors):
 * Call installRetry() BEFORE registering the 401 refresh interceptor so that
 * the retry handler runs first.  On 503/network the retry handler retries
 * transparently; if every attempt fails the rejection propagates to the 401
 * handler (which will correctly show one error toast and reject).  On 401
 * shouldRetry() returns false immediately, so the error flows through to the
 * existing refresh logic untouched.
 */
export function installRetry(client: AxiosInstance, opts?: RetryOptions): void {
  const maxRetries = opts?.maxRetries ?? DEFAULT_MAX_RETRIES
  const methods = opts?.methods ?? DEFAULT_METHODS
  const statuses = opts?.statuses ?? DEFAULT_STATUSES
  const delayFn = opts?.delayFn ?? ((attempt: number) => backoffDelay(attempt))

  const resolvedOpts: RetryOptions = { maxRetries, methods, statuses, delayFn }

  client.interceptors.response.use(
    undefined, // pass successes straight through
    async (error: AxiosError) => {
      const config = error.config as RetryConfig | undefined
      if (!config) return Promise.reject(error)

      const attempt = config._retryAttempt ?? 0

      if (shouldRetry(error, attempt, resolvedOpts)) {
        config._retryAttempt = attempt + 1
        const delay = delayFn(attempt)
        if (delay > 0) {
          await new Promise<void>((resolve) => setTimeout(resolve, delay))
        }
        return client(config)
      }

      return Promise.reject(error)
    },
  )
}
