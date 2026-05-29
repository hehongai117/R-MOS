/**
 * Tests for config/statusLabels.ts and config/agentIntents.ts
 *
 * Verifies that all status keys are present, each entry has the correct
 * structure, fallback values are valid, and agent intent / quick-action
 * references are consistent.
 */

import { describe, it, expect } from 'vitest'

import {
  ATTEMPT_STATUS,
  ATTEMPT_STATUS_FALLBACK,
  ROBOT_MODEL_STATUS,
  ANALYSIS_STATUS,
} from '../statusLabels'

import {
  INTENT_OPTIONS,
  QUICK_ACTIONS,
  RISK_STATUS_MAP,
} from '../agentIntents'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** LucideIcon components may appear as function or object in jsdom */
function isIconLike(value: unknown): boolean {
  return ['function', 'object'].includes(typeof value) && value !== null
}

// ---------------------------------------------------------------------------
// statusLabels — ATTEMPT_STATUS
// ---------------------------------------------------------------------------

describe('ATTEMPT_STATUS', () => {
  const REQUIRED_KEYS = ['in_progress', 'completed', 'graded', 'abandoned']

  it('contains all required keys', () => {
    for (const key of REQUIRED_KEYS) {
      expect(ATTEMPT_STATUS).toHaveProperty(key)
    }
  })

  it('has no extra unexpected keys', () => {
    expect(Object.keys(ATTEMPT_STATUS).sort()).toEqual([...REQUIRED_KEYS].sort())
  })

  it.each(REQUIRED_KEYS)('"%s" entry has a non-empty label and variant', (key) => {
    const entry = ATTEMPT_STATUS[key]
    expect(typeof entry.label).toBe('string')
    expect(entry.label.length).toBeGreaterThan(0)
    expect(typeof entry.variant).toBe('string')
    expect(entry.variant.length).toBeGreaterThan(0)
  })

  it('"in_progress" label is in Chinese', () => {
    expect(ATTEMPT_STATUS.in_progress.label).toBe('进行中')
  })

  it('"in_progress" variant is "active"', () => {
    expect(ATTEMPT_STATUS.in_progress.variant).toBe('active')
  })

  it('"completed" variant is "success"', () => {
    expect(ATTEMPT_STATUS.completed.variant).toBe('success')
  })
})

// ---------------------------------------------------------------------------
// statusLabels — ATTEMPT_STATUS_FALLBACK
// ---------------------------------------------------------------------------

describe('ATTEMPT_STATUS_FALLBACK', () => {
  it('has a non-empty label', () => {
    expect(typeof ATTEMPT_STATUS_FALLBACK.label).toBe('string')
    expect(ATTEMPT_STATUS_FALLBACK.label.length).toBeGreaterThan(0)
  })

  it('has a non-empty variant', () => {
    expect(typeof ATTEMPT_STATUS_FALLBACK.variant).toBe('string')
    expect(ATTEMPT_STATUS_FALLBACK.variant.length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// statusLabels — ROBOT_MODEL_STATUS
// ---------------------------------------------------------------------------

describe('ROBOT_MODEL_STATUS', () => {
  const REQUIRED_KEYS = ['draft', 'analyzing', 'ready']

  it('contains all required keys', () => {
    for (const key of REQUIRED_KEYS) {
      expect(ROBOT_MODEL_STATUS).toHaveProperty(key)
    }
  })

  it.each(REQUIRED_KEYS)('"%s" entry has a non-empty label and className', (key) => {
    const entry = ROBOT_MODEL_STATUS[key]
    expect(typeof entry.label).toBe('string')
    expect(entry.label.length).toBeGreaterThan(0)
    expect(typeof entry.className).toBe('string')
    expect(entry.className.length).toBeGreaterThan(0)
  })

  it('"draft" label is "草稿"', () => {
    expect(ROBOT_MODEL_STATUS.draft.label).toBe('草稿')
  })

  it('"ready" label is "已发布"', () => {
    expect(ROBOT_MODEL_STATUS.ready.label).toBe('已发布')
  })
})

// ---------------------------------------------------------------------------
// statusLabels — ANALYSIS_STATUS
// ---------------------------------------------------------------------------

describe('ANALYSIS_STATUS', () => {
  const REQUIRED_KEYS = ['pending', 'running', 'completed', 'failed']

  it('contains all required keys', () => {
    for (const key of REQUIRED_KEYS) {
      expect(ANALYSIS_STATUS).toHaveProperty(key)
    }
  })

  it.each(REQUIRED_KEYS)('"%s" entry has label, icon, and className', (key) => {
    const entry = ANALYSIS_STATUS[key]
    expect(typeof entry.label).toBe('string')
    expect(entry.label.length).toBeGreaterThan(0)
    expect(isIconLike(entry.icon)).toBe(true)
    expect(typeof entry.className).toBe('string')
    expect(entry.className.length).toBeGreaterThan(0)
  })

  it('all icons are Lucide-compatible (function or object, non-null)', () => {
    for (const [, entry] of Object.entries(ANALYSIS_STATUS)) {
      expect(isIconLike(entry.icon)).toBe(true)
    }
  })

  it('"pending" label is "等待中"', () => {
    expect(ANALYSIS_STATUS.pending.label).toBe('等待中')
  })

  it('"failed" className includes red color', () => {
    expect(ANALYSIS_STATUS.failed.className).toContain('red')
  })
})

// ---------------------------------------------------------------------------
// agentIntents — INTENT_OPTIONS
// ---------------------------------------------------------------------------

describe('INTENT_OPTIONS', () => {
  const REQUIRED_VALUES = [
    'general',
    'execute-task',
    'delegate-diagnoser',
    'read-kb',
    'write-kb',
    'delegate-coach',
  ]

  it('has at least 5 entries', () => {
    expect(INTENT_OPTIONS.length).toBeGreaterThanOrEqual(5)
  })

  it('contains all required intent values', () => {
    const values = INTENT_OPTIONS.map((o) => o.value)
    for (const v of REQUIRED_VALUES) {
      expect(values).toContain(v)
    }
  })

  it.each(INTENT_OPTIONS)('intent "$value" has a non-empty label', ({ value, label }) => {
    expect(typeof value).toBe('string')
    expect(value.length).toBeGreaterThan(0)
    expect(typeof label).toBe('string')
    expect(label.length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// agentIntents — QUICK_ACTIONS
// ---------------------------------------------------------------------------

describe('QUICK_ACTIONS', () => {
  it('has at least one quick action', () => {
    expect(QUICK_ACTIONS.length).toBeGreaterThan(0)
  })

  it.each(QUICK_ACTIONS)('action "$id" has required fields', ({ id, title, desc, prompt, intent, icon }) => {
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
    expect(typeof title).toBe('string')
    expect(title.length).toBeGreaterThan(0)
    expect(typeof desc).toBe('string')
    expect(desc.length).toBeGreaterThan(0)
    expect(typeof prompt).toBe('string')
    expect(prompt.length).toBeGreaterThan(0)
    expect(typeof intent).toBe('string')
    expect(intent.length).toBeGreaterThan(0)
    expect(isIconLike(icon)).toBe(true)
  })

  it('every quick action intent references a valid INTENT_OPTIONS value', () => {
    const validValues = new Set(INTENT_OPTIONS.map((o) => o.value))
    for (const action of QUICK_ACTIONS) {
      expect(validValues.has(action.intent)).toBe(true)
    }
  })

  it('has 6 quick actions matching the spec', () => {
    expect(QUICK_ACTIONS.length).toBe(6)
  })
})

// ---------------------------------------------------------------------------
// agentIntents — RISK_STATUS_MAP
// ---------------------------------------------------------------------------

describe('RISK_STATUS_MAP', () => {
  it('covers R0 through R3', () => {
    expect(RISK_STATUS_MAP).toHaveProperty('R0')
    expect(RISK_STATUS_MAP).toHaveProperty('R1')
    expect(RISK_STATUS_MAP).toHaveProperty('R2')
    expect(RISK_STATUS_MAP).toHaveProperty('R3')
  })

  it('R0 maps to "success"', () => {
    expect(RISK_STATUS_MAP['R0']).toBe('success')
  })

  it('R1 maps to "success"', () => {
    expect(RISK_STATUS_MAP['R1']).toBe('success')
  })

  it('R2 maps to "warning"', () => {
    expect(RISK_STATUS_MAP['R2']).toBe('warning')
  })

  it('R3 maps to "error"', () => {
    expect(RISK_STATUS_MAP['R3']).toBe('error')
  })

  it('all values are valid status tokens', () => {
    const VALID: Array<'success' | 'warning' | 'error'> = ['success', 'warning', 'error']
    for (const [, status] of Object.entries(RISK_STATUS_MAP)) {
      expect(VALID).toContain(status)
    }
  })
})
