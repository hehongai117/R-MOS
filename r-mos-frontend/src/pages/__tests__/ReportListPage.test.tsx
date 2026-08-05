import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import ReportListPage from '../ReportListPage'

const mockListTasks = vi.fn()
vi.mock('@/api/task', () => ({
  listTasks: (...args: unknown[]) => mockListTasks(...args),
}))

// antd Table 的响应式分页在 jsdom 下需要 matchMedia
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

const renderPage = () =>
  render(
    <MemoryRouter>
      <ReportListPage />
    </MemoryRouter>,
  )

describe('ReportListPage', () => {
  beforeEach(() => {
    mockListTasks.mockReset()
  })

  it('renders task rows returned by the API', async () => {
    mockListTasks.mockResolvedValue({
      items: [
        {
          id: 7,
          title: '关节润滑维保',
          status: 'completed',
          current_step_index: 3,
          pass_score: 70,
          final_score: 88,
          completed_at: '2026-08-05T02:00:00Z',
          created_at: '2026-08-05T01:00:00Z',
          updated_at: '2026-08-05T02:00:00Z',
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    })

    renderPage()

    expect(await screen.findByText('关节润滑维保')).toBeInTheDocument()
    expect(screen.getByText('88')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '查看报告' })).toBeInTheDocument()
  })

  it('requests the first page with offset 0', async () => {
    mockListTasks.mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 })

    renderPage()

    await waitFor(() => {
      expect(mockListTasks).toHaveBeenCalledWith({ limit: 10, offset: 0 })
    })
  })

  it('shows an empty hint when there are no tasks', async () => {
    mockListTasks.mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 })

    renderPage()

    expect(await screen.findByText('暂无维保任务记录')).toBeInTheDocument()
  })

  it('surfaces API errors instead of rendering a blank page', async () => {
    mockListTasks.mockRejectedValue({ response: { data: { detail: '服务不可用' } } })

    renderPage()

    expect(await screen.findByText('无法加载列表')).toBeInTheDocument()
    expect(screen.getByText('服务不可用')).toBeInTheDocument()
  })
})
