import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, describe, expect, it, vi } from 'vitest'

const viewerState = vi.hoisted(() => ({
  Atom01ViewerMock: ({
    jointAngles = {},
    faultJoints = [],
  }: {
    jointAngles?: Record<string, number>
    faultJoints?: string[]
  }) => {
    const formatAngle = (jointName: string) =>
      jointName in jointAngles ? jointAngles[jointName].toFixed(2) : 'unset'

    return (
      <div
        data-fault-count={faultJoints.length}
        data-left-knee={formatAngle('left_knee_joint')}
        data-left-thigh-pitch={formatAngle('left_thigh_pitch_joint')}
        data-right-knee={formatAngle('right_knee_joint')}
        data-right-thigh-pitch={formatAngle('right_thigh_pitch_joint')}
        data-testid="atom01-viewer"
      />
    )
  },
}))

vi.mock('@/components/Viewer3D', () => ({
  Atom01Viewer: viewerState.Atom01ViewerMock,
}))

import Atom01DemoPage from '@/pages/Atom01DemoPage'

describe('Atom01DemoPage', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it('applies an explicit neutral pose when returning to stand', async () => {
    const user = userEvent.setup()
    render(<Atom01DemoPage />)

    const viewer = screen.getByTestId('atom01-viewer')

    await user.click(screen.getByRole('button', { name: '行 走' }))

    expect(viewer.getAttribute('data-left-thigh-pitch')).toBe('0.50')
    expect(viewer.getAttribute('data-right-knee')).toBe('0.20')

    await user.click(screen.getByRole('button', { name: '站 立' }))

    expect(viewer.getAttribute('data-left-thigh-pitch')).toBe('0.00')
    expect(viewer.getAttribute('data-right-knee')).toBe('0.00')
  })

  it('resets pose and clears fault joints', async () => {
    const user = userEvent.setup()
    render(<Atom01DemoPage />)

    const viewer = screen.getByTestId('atom01-viewer')

    await user.click(screen.getByRole('button', { name: '行 走' }))
    await user.click(screen.getAllByRole('switch', { name: '故障' })[0])

    expect(viewer.getAttribute('data-fault-count')).toBe('1')

    await user.click(screen.getByRole('button', { name: /重置姿态/i }))

    expect(viewer.getAttribute('data-left-thigh-pitch')).toBe('0.00')
    expect(viewer.getAttribute('data-right-thigh-pitch')).toBe('0.00')
    expect(viewer.getAttribute('data-fault-count')).toBe('0')
  })
})
