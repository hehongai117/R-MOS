import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AnalysisStatusPanel } from '../AnalysisStatusPanel'
import type { AnalysisTask } from '@/types/robotModel'

const makeTask = (overrides: Partial<AnalysisTask> = {}): AnalysisTask => ({
  id: 1,
  robot_model_id: 1,
  task_type: 'full',
  status: 'pending',
  input_document_ids: [1, 2],
  output_summary: null,
  error_message: null,
  completed_at: null,
  created_at: '2026-01-01T12:00:00Z',
  ...overrides,
})

describe('AnalysisStatusPanel', () => {
  it('shows empty state when no tasks', () => {
    render(<AnalysisStatusPanel tasks={[]} loading={false} onTrigger={vi.fn()} />)
    expect(screen.getByText('暂无分析任务')).toBeInTheDocument()
  })

  it('renders task list with status', () => {
    const tasks = [
      makeTask({ id: 1, status: 'completed' }),
      makeTask({ id: 2, status: 'running' }),
    ]
    render(<AnalysisStatusPanel tasks={tasks} loading={false} onTrigger={vi.fn()} />)
    expect(screen.getByText('已完成')).toBeInTheDocument()
    expect(screen.getByText('运行中')).toBeInTheDocument()
  })

  it('shows error message for failed tasks', () => {
    const tasks = [makeTask({ status: 'failed', error_message: '解析失败：格式不支持' })]
    render(<AnalysisStatusPanel tasks={tasks} loading={false} onTrigger={vi.fn()} />)
    expect(screen.getByText('解析失败：格式不支持')).toBeInTheDocument()
  })

  it('calls onTrigger when trigger button clicked', () => {
    const onTrigger = vi.fn()
    render(<AnalysisStatusPanel tasks={[]} loading={false} onTrigger={onTrigger} canTrigger />)
    fireEvent.click(screen.getByRole('button', { name: '触发分析' }))
    expect(onTrigger).toHaveBeenCalled()
  })

  it('disables trigger when canTrigger is false', () => {
    render(
      <AnalysisStatusPanel tasks={[]} loading={false} onTrigger={vi.fn()} canTrigger={false} />,
    )
    expect(screen.queryByRole('button', { name: '触发分析' })).not.toBeInTheDocument()
  })
})
