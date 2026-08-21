import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ReportPage from '../ReportPage'

const mockGetTaskReport = vi.fn()
vi.mock('@/api/task', () => ({
  getTaskReport: (...args: unknown[]) => mockGetTaskReport(...args),
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

const baseReport = {
  task_id: 42,
  task_title: '膝关节轴承更换',
  sop_name: '膝关节轴承更换 SOP',
  user_id: 7,
  started_at: '2026-08-21T01:00:00Z',
  completed_at: '2026-08-21T01:05:00Z',
  total_duration_seconds: 300,
  expected_duration_seconds: 600,
  final_score: 100,
  pass_score: 70,
  is_passed: true,
  score_breakdown: { professionalism: 25, compliance: 25, efficiency: 25, safety: 25 },
  step_scores: [],
  total_steps: 22,
  completed_steps: 22,
  skipped_steps: 0,
  error_count: 0,
  recommendations: [],
  generated_at: '2026-08-21T01:05:00Z',
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/reports/42']}>
      <Routes>
        <Route path="/reports/:taskId" element={<ReportPage />} />
      </Routes>
    </MemoryRouter>,
  )

describe('ReportPage checklist evidence', () => {
  beforeEach(() => {
    mockGetTaskReport.mockReset()
  })

  it('renders kit and verification record sections when evidence exists', async () => {
    mockGetTaskReport.mockResolvedValue({
      ...baseReport,
      checklist_evidence: [
        {
          step_index: 1,
          evidence_type: 'kit_checklist',
          evidence_value: {
            required_items: ['6205 轴承', '拉拔器'],
            confirmed_items: ['6205 轴承', '拉拔器'],
          },
          is_compliant: true,
        },
        {
          step_index: 22,
          evidence_type: 'verify_checklist',
          evidence_value: {
            required_items: ['轴承转动顺畅', '防护罩已复位'],
            confirmed_items: ['轴承转动顺畅'],
          },
          is_compliant: false,
        },
      ],
    })

    renderPage()

    expect(await screen.findByText('齐套记录')).toBeInTheDocument()
    expect(screen.getByText('验收记录')).toBeInTheDocument()
    expect(screen.getByText('6205 轴承')).toBeInTheDocument()
    expect(screen.getByText('防护罩已复位')).toBeInTheDocument()
    expect(screen.getByText('未通过')).toBeInTheDocument()
  })

  it('does not render either section when historical reports have no checklist evidence', async () => {
    mockGetTaskReport.mockResolvedValue(baseReport)

    renderPage()

    expect(await screen.findByText('任务摘要')).toBeInTheDocument()
    expect(screen.queryByText('齐套记录')).not.toBeInTheDocument()
    expect(screen.queryByText('验收记录')).not.toBeInTheDocument()
  })
})
