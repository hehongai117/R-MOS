import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useRobotStore } from '../robotStore'

const baseMockRobot = {
  id: 1,
  brand: 'R-MOS',
  model_name: 'ATOM-01',
  version: '1.0',
  owner_teacher_id: 10,
  visibility: 'private' as const,
  status: 'draft' as const,
  description: null,
  thumbnail_path: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

vi.mock('@/api/robots', () => {
  const base = {
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
  }
  return {
    listRobots: vi.fn().mockResolvedValue({ items: [base], total: 1 }),
    createRobot: vi.fn().mockResolvedValue({ ...base, id: 2, brand: 'New' }),
    updateRobot: vi.fn().mockResolvedValue({ ...base, brand: 'Updated' }),
    deleteRobot: vi.fn().mockResolvedValue(undefined),
    togglePublish: vi.fn().mockResolvedValue({ ...base, status: 'ready' }),
    toggleVisibility: vi.fn().mockResolvedValue({ ...base, visibility: 'shared' }),
  }
})

// Suppress antd message calls in test
vi.mock('antd', () => ({
  message: { error: vi.fn(), success: vi.fn() },
}))

describe('robotStore', () => {
  beforeEach(() => {
    useRobotStore.setState({ robots: [], selectedRobotId: null, isLoading: false })
  })

  it('fetchRobots loads robots into state', async () => {
    await useRobotStore.getState().fetchRobots()
    expect(useRobotStore.getState().robots).toHaveLength(1)
    expect(useRobotStore.getState().robots[0].brand).toBe('R-MOS')
  })

  it('addRobot prepends to list and selects it', async () => {
    useRobotStore.setState({ robots: [baseMockRobot] })
    const result = await useRobotStore.getState().addRobot({ brand: 'New', model_name: 'N1' })
    expect(result.id).toBe(2)
    expect(useRobotStore.getState().robots[0].id).toBe(2)
    expect(useRobotStore.getState().selectedRobotId).toBe(2)
  })

  it('removeRobot removes from list and resets selection', async () => {
    useRobotStore.setState({ robots: [baseMockRobot], selectedRobotId: 1 })
    await useRobotStore.getState().removeRobot(1)
    expect(useRobotStore.getState().robots).toHaveLength(0)
    expect(useRobotStore.getState().selectedRobotId).toBeNull()
  })

  it('selectRobot updates selectedRobotId', () => {
    useRobotStore.getState().selectRobot(42)
    expect(useRobotStore.getState().selectedRobotId).toBe(42)
  })

  it('togglePublish updates robot status in list', async () => {
    useRobotStore.setState({ robots: [baseMockRobot] })
    await useRobotStore.getState().togglePublish(1)
    expect(useRobotStore.getState().robots[0].status).toBe('ready')
  })

  it('toggleVisibility updates robot visibility in list', async () => {
    useRobotStore.setState({ robots: [baseMockRobot] })
    await useRobotStore.getState().toggleVisibility(1)
    expect(useRobotStore.getState().robots[0].visibility).toBe('shared')
  })
})
