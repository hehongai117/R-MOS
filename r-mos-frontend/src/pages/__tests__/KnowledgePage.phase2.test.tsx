import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

// Mock store
const mockFetchRobots = vi.fn()
const mockSelectRobot = vi.fn()
const mockRobots = [
  {
    id: 1,
    brand: 'R-MOS',
    model_name: 'ATOM-01',
    version: '1.0',
    owner_teacher_id: 10,
    visibility: 'private',
    status: 'ready',
    description: null,
    thumbnail_path: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
]

vi.mock('@/store/robotStore', () => ({
  useRobotStore: vi.fn((selector) =>
    selector({
      robots: mockRobots,
      selectedRobotId: 1,
      isLoading: false,
      fetchRobots: mockFetchRobots,
      selectRobot: mockSelectRobot,
      addRobot: vi.fn(),
      togglePublish: vi.fn(),
      toggleVisibility: vi.fn(),
    }),
  ),
  useSelectedRobot: vi.fn(() => mockRobots[0]),
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector) =>
    selector({
      user: { role: 'teacher', user_id: 10, email: 'teacher@test.com' },
    }),
  ),
}))

vi.mock('@/api/agent', () => ({
  searchKnowledge: vi.fn().mockResolvedValue({ results: [] }),
  createKnowledge: vi.fn(),
  submitKnowledgeForReview: vi.fn(),
  approveKnowledge: vi.fn(),
}))

vi.mock('@/api/robotKnowledge', () => ({
  listRobotProjects: vi.fn().mockResolvedValue({ projects: [] }),
  getRobotProjectUploadJob: vi.fn(),
  uploadRobotProjectPackage: vi.fn(),
}))

vi.mock('@/api/robots', () => ({
  listAnalysisTasks: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}))

vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}))

Object.defineProperty(window, 'getComputedStyle', {
  configurable: true,
  value: () => ({
    getPropertyValue: () => '',
  }),
})

describe('KnowledgePage with robot sidebar (Phase 2)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders robot sidebar for teacher', async () => {
    const KnowledgePage = (await import('../KnowledgePage')).default
    render(<KnowledgePage />)
    await waitFor(() => {
      const matches = screen.getAllByText('ATOM-01')
      expect(matches.length).toBeGreaterThan(0)
      expect(matches[0]).toBeInTheDocument()
    })
  })

  it('calls fetchRobots on mount', async () => {
    const KnowledgePage = (await import('../KnowledgePage')).default
    render(<KnowledgePage />)
    expect(mockFetchRobots).toHaveBeenCalled()
  })
})
