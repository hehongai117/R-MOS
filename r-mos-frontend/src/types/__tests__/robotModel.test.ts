import { describe, expect, it } from 'vitest'
import { canPublish, isOwnedRobot, type RobotModel } from '../robotModel'

function makeRobot(overrides: Partial<RobotModel> = {}): RobotModel {
  return {
    id: 1,
    brand: 'R-MOS',
    model_name: 'ATOM-01',
    version: '1.0',
    owner_teacher_id: 10,
    visibility: 'private',
    status: 'draft',
    description: null,
    thumbnail_path: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('isOwnedRobot', () => {
  it('returns true when userId matches owner_teacher_id', () => {
    expect(isOwnedRobot(makeRobot({ owner_teacher_id: 10 }), 10)).toBe(true)
  })

  it('returns false when userId does not match', () => {
    expect(isOwnedRobot(makeRobot({ owner_teacher_id: 10 }), 99)).toBe(false)
  })

  it('returns false when userId is undefined', () => {
    expect(isOwnedRobot(makeRobot(), undefined)).toBe(false)
  })
})

describe('canPublish', () => {
  it('returns true for draft status', () => {
    expect(canPublish(makeRobot({ status: 'draft' }))).toBe(true)
  })

  it('returns true for ready status (toggle unpublish)', () => {
    expect(canPublish(makeRobot({ status: 'ready' }))).toBe(true)
  })

  it('returns false for analyzing status', () => {
    expect(canPublish(makeRobot({ status: 'analyzing' }))).toBe(false)
  })
})
