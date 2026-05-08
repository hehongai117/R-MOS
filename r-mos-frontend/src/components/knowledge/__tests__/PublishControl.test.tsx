import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PublishControl } from '../PublishControl'
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

describe('PublishControl', () => {
  it('shows "发布" button for draft robot', () => {
    render(
      <PublishControl robot={makeRobot({ status: 'draft' })} onPublish={vi.fn()} onToggleVisibility={vi.fn()} />,
    )
    expect(screen.getByRole('button', { name: '发布' })).toBeInTheDocument()
  })

  it('shows "取消发布" button for ready robot', () => {
    render(
      <PublishControl robot={makeRobot({ status: 'ready' })} onPublish={vi.fn()} onToggleVisibility={vi.fn()} />,
    )
    expect(screen.getByRole('button', { name: '取消发布' })).toBeInTheDocument()
  })

  it('disables publish for analyzing robot', () => {
    render(
      <PublishControl
        robot={makeRobot({ status: 'analyzing' })}
        onPublish={vi.fn()}
        onToggleVisibility={vi.fn()}
      />,
    )
    const btn = screen.getByRole('button', { name: '分析中...' })
    expect(btn).toBeDisabled()
  })

  it('shows visibility toggle', () => {
    render(
      <PublishControl
        robot={makeRobot({ visibility: 'private' })}
        onPublish={vi.fn()}
        onToggleVisibility={vi.fn()}
      />,
    )
    expect(screen.getByText('私有')).toBeInTheDocument()
  })

  it('calls onPublish when publish button clicked', () => {
    const onPublish = vi.fn()
    render(
      <PublishControl robot={makeRobot({ status: 'draft' })} onPublish={onPublish} onToggleVisibility={vi.fn()} />,
    )
    fireEvent.click(screen.getByRole('button', { name: '发布' }))
    expect(onPublish).toHaveBeenCalled()
  })

  it('calls onToggleVisibility when visibility button clicked', () => {
    const onToggle = vi.fn()
    render(
      <PublishControl robot={makeRobot()} onPublish={vi.fn()} onToggleVisibility={onToggle} />,
    )
    fireEvent.click(screen.getByText('私有'))
    expect(onToggle).toHaveBeenCalled()
  })

  it('shows "共享" label when visibility is shared', () => {
    render(
      <PublishControl
        robot={makeRobot({ visibility: 'shared' })}
        onPublish={vi.fn()}
        onToggleVisibility={vi.fn()}
      />,
    )
    expect(screen.getByText('共享')).toBeInTheDocument()
  })
})
