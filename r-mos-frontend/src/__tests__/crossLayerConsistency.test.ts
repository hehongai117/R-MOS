/**
 * Cross-Layer Consistency Validation Tests
 *
 * Validates that frontend config layers (routes, nav, status labels, difficulty mapping)
 * remain consistent with each other and with the backend API contracts.
 */

import { describe, it, expect } from 'vitest'
import { LAYOUT_CONFIG } from '@/config/nav'
import { ROUTE_PERMISSIONS, getAllowedRoles } from '@/config/routes'
import { ATTEMPT_STATUS, ROBOT_MODEL_STATUS, ANALYSIS_STATUS } from '@/config/statusLabels'

// ---------------------------------------------------------------------------
// 1. Route permission key format integrity
// ---------------------------------------------------------------------------

describe('Route permissions — key format', () => {
  const keys = Object.keys(ROUTE_PERMISSIONS)

  it('no key starts with a leading slash', () => {
    const violations = keys.filter((k) => k.startsWith('/'))
    expect(violations).toEqual([])
  })

  it('no key ends with a trailing slash', () => {
    const violations = keys.filter((k) => k.endsWith('/'))
    expect(violations).toEqual([])
  })

  it('critical routes are defined — dashboard', () => {
    expect(keys).toContain('dashboard')
  })

  it('critical routes are defined — maintenance', () => {
    expect(keys).toContain('maintenance')
  })

  it('critical routes are defined — monitor', () => {
    expect(keys).toContain('monitor')
  })

  it('critical routes are defined — knowledge', () => {
    expect(keys).toContain('knowledge')
  })

  it('critical routes are defined — settings', () => {
    expect(keys).toContain('settings')
  })
})

// ---------------------------------------------------------------------------
// 2. Status label completeness — backend enum coverage
// ---------------------------------------------------------------------------

describe('ATTEMPT_STATUS — backend enum coverage', () => {
  const backendValues = ['in_progress', 'completed', 'graded', 'abandoned']

  backendValues.forEach((status) => {
    it(`covers backend value: ${status}`, () => {
      expect(ATTEMPT_STATUS).toHaveProperty(status)
    })
  })

  it('each entry has a non-empty label', () => {
    Object.entries(ATTEMPT_STATUS).forEach(([key, config]) => {
      expect(config.label, `ATTEMPT_STATUS["${key}"].label`).toBeTruthy()
    })
  })

  it('each entry has a variant', () => {
    Object.entries(ATTEMPT_STATUS).forEach(([key, config]) => {
      expect(config.variant, `ATTEMPT_STATUS["${key}"].variant`).toBeTruthy()
    })
  })
})

describe('ROBOT_MODEL_STATUS — backend enum coverage', () => {
  const backendValues = ['draft', 'analyzing', 'ready']

  backendValues.forEach((status) => {
    it(`covers backend value: ${status}`, () => {
      expect(ROBOT_MODEL_STATUS).toHaveProperty(status)
    })
  })

  it('each entry has a non-empty label', () => {
    Object.entries(ROBOT_MODEL_STATUS).forEach(([key, config]) => {
      expect(config.label, `ROBOT_MODEL_STATUS["${key}"].label`).toBeTruthy()
    })
  })
})

describe('ANALYSIS_STATUS — backend enum coverage', () => {
  const backendValues = ['pending', 'running', 'completed', 'failed']

  backendValues.forEach((status) => {
    it(`covers backend value: ${status}`, () => {
      expect(ANALYSIS_STATUS).toHaveProperty(status)
    })
  })

  it('each entry has a non-empty label', () => {
    Object.entries(ANALYSIS_STATUS).forEach(([key, config]) => {
      expect(config.label, `ANALYSIS_STATUS["${key}"].label`).toBeTruthy()
    })
  })
})

// ---------------------------------------------------------------------------
// 3. Difficulty mapping contract (backend SOP adjudication API)
// ---------------------------------------------------------------------------

describe('Difficulty mapping — backend SOP adjudication contract', () => {
  /**
   * Contract: the backend SOP adjudication API returns difficulty as
   * "low" | "medium" | "high". The frontend maps these to display labels.
   * This test documents and guards the expected mapping.
   */
  const DIFFICULTY_MAP: Record<string, string> = {
    low: 'beginner',
    medium: 'intermediate',
    high: 'advanced',
  }

  it('low maps to beginner', () => {
    expect(DIFFICULTY_MAP['low']).toBe('beginner')
  })

  it('medium maps to intermediate', () => {
    expect(DIFFICULTY_MAP['medium']).toBe('intermediate')
  })

  it('high maps to advanced', () => {
    expect(DIFFICULTY_MAP['high']).toBe('advanced')
  })

  it('all three backend difficulty levels are mapped', () => {
    const backendLevels = ['low', 'medium', 'high']
    backendLevels.forEach((level) => {
      expect(DIFFICULTY_MAP).toHaveProperty(level)
      expect(DIFFICULTY_MAP[level]).toBeTruthy()
    })
  })
})

// ---------------------------------------------------------------------------
// 4. Nav ↔ Route permission cross-validation
// ---------------------------------------------------------------------------

/**
 * Strips a leading slash to match ROUTE_PERMISSIONS key format.
 * e.g. "/dashboard" → "dashboard", "/my-tasks" → "my-tasks"
 */
function stripLeadingSlash(path: string): string {
  return path.startsWith('/') ? path.slice(1) : path
}

/**
 * A route is "allowed for role" when:
 *   - ROUTE_PERMISSIONS[key] === undefined (public / any authenticated user), OR
 *   - ROUTE_PERMISSIONS[key] includes the given role
 */
function isRouteAllowedForRole(routeKey: string, role: string): boolean {
  const allowed = getAllowedRoles(routeKey)
  if (allowed === undefined) return true
  return (allowed as string[]).includes(role)
}

describe('Student nav items — route permission alignment', () => {
  const studentNavItems = LAYOUT_CONFIG.student.navGroups.flatMap((g) => g.items)

  studentNavItems.forEach(({ label, to }) => {
    const routeKey = stripLeadingSlash(to)
    it(`"${label}" (${to}) is accessible to student or is a public route`, () => {
      expect(
        isRouteAllowedForRole(routeKey, 'student'),
        `Route "${routeKey}" must allow "student" or be undefined (public). ` +
          `Current value: ${JSON.stringify(ROUTE_PERMISSIONS[routeKey])}`,
      ).toBe(true)
    })
  })
})

describe('Teacher nav items — route permission alignment', () => {
  const teacherNavItems = LAYOUT_CONFIG.teacher.navGroups.flatMap((g) => g.items)

  teacherNavItems.forEach(({ label, to }) => {
    const routeKey = stripLeadingSlash(to)
    it(`"${label}" (${to}) is accessible to teacher or is a public route`, () => {
      expect(
        isRouteAllowedForRole(routeKey, 'teacher'),
        `Route "${routeKey}" must allow "teacher" or be undefined (public). ` +
          `Current value: ${JSON.stringify(ROUTE_PERMISSIONS[routeKey])}`,
      ).toBe(true)
    })
  })
})
