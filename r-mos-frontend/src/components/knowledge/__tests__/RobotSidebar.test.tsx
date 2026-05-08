import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RobotSidebar } from '../RobotSidebar'
import type { RobotModel } from '@/types/robotModel'

const makeRobot = (overrides: Partial<RobotModel> = {}): RobotModel => ({
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
})

describe('RobotSidebar', () => {
  it('renders robot list items', () => {
    const robots = [
      makeRobot({ id: 1, brand: 'R-MOS', model_name: 'ATOM-01' }),
      makeRobot({ id: 2, brand: 'UBTech', model_name: 'Walker X' }),
    ]
    render(
      <RobotSidebar
        robots={robots}
        selectedRobotId={1}
        loading={false}
        onSelect={vi.fn()}
        onAdd={vi.fn()}
      />,
    )
    expect(screen.getByText('ATOM-01')).toBeInTheDocument()
    expect(screen.getByText('Walker X')).toBeInTheDocument()
  })

  it('highlights selected robot', () => {
    const robots = [makeRobot({ id: 1 }), makeRobot({ id: 2, model_name: 'ATOM-02' })]
    render(
      <RobotSidebar robots={robots} selectedRobotId={1} loading={false} onSelect={vi.fn()} onAdd={vi.fn()} />,
    )
    const selected = screen.getByText('ATOM-01').closest('[data-selected]')
    expect(selected?.getAttribute('data-selected')).toBe('true')
  })

  it('calls onSelect when clicking a robot', () => {
    const onSelect = vi.fn()
    const robots = [makeRobot({ id: 1 }), makeRobot({ id: 2, model_name: 'X2' })]
    render(
      <RobotSidebar robots={robots} selectedRobotId={1} loading={false} onSelect={onSelect} onAdd={vi.fn()} />,
    )
    fireEvent.click(screen.getByText('X2'))
    expect(onSelect).toHaveBeenCalledWith(2)
  })

  it('calls onAdd when clicking add button', () => {
    const onAdd = vi.fn()
    render(
      <RobotSidebar robots={[]} selectedRobotId={null} loading={false} onSelect={vi.fn()} onAdd={onAdd} />,
    )
    fireEvent.click(screen.getByRole('button', { name: /添加机器人/i }))
    expect(onAdd).toHaveBeenCalled()
  })

  it('shows status indicator for analyzing robots', () => {
    const robots = [makeRobot({ id: 1, status: 'analyzing' })]
    render(
      <RobotSidebar robots={robots} selectedRobotId={null} loading={false} onSelect={vi.fn()} onAdd={vi.fn()} />,
    )
    expect(screen.getByText('分析中')).toBeInTheDocument()
  })

  it('shows status indicator for ready robots', () => {
    const robots = [makeRobot({ id: 1, status: 'ready' })]
    render(
      <RobotSidebar robots={robots} selectedRobotId={null} loading={false} onSelect={vi.fn()} onAdd={vi.fn()} />,
    )
    expect(screen.getByText('已发布')).toBeInTheDocument()
  })
})
