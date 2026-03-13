import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

const assemblyState = vi.hoisted(() => ({
  explodeManifest: {
    version: '2026-03-13',
    robotId: 'atom01',
    views: [
      {
        id: 'torso_service_view',
        focus_node_id: 'torso_link',
        camera: {
          projection: 'orthographic',
          position: [1.15, 0.58, 0.72],
          target: [0.04, 0, 0.28],
        },
      },
    ],
    sequences: [
      {
        id: 'torso_cover_removal',
        step_index: 1,
        node_ids: ['torso_shell_front'],
        direction: [0, 0, 1],
        distance: 0.18,
        anchor_node_id: 'torso_link',
      },
      {
        id: 'torso_secondary_release',
        step_index: 2,
        node_ids: ['torso_shell_front'],
        direction: [0, 1, 0],
        distance: 0.1,
        anchor_node_id: 'torso_link',
      },
    ],
  },
}))

const viewerState = vi.hoisted(() => ({
  Atom01ViewerMock: ({
    jointAngles = {},
    faultJoints = [],
    interactiveMode = false,
    showSubParts = false,
    explodeAmount = 0,
    explodeStepIndex = null,
    subPartEnabledNames = [],
    cameraProjection = 'perspective',
    cameraPosition = [1.5, 1, 1.5],
    cameraTarget = [0, 0.3, 0],
  }: {
    jointAngles?: Record<string, number>
    faultJoints?: string[]
    interactiveMode?: boolean
    showSubParts?: boolean
    explodeAmount?: number
    explodeStepIndex?: number | null
    subPartEnabledNames?: string[]
    cameraProjection?: 'orthographic' | 'perspective'
    cameraPosition?: [number, number, number]
    cameraTarget?: [number, number, number]
  }) => {
    const formatAngle = (jointName: string) =>
      jointName in jointAngles ? jointAngles[jointName].toFixed(2) : 'unset'

    return (
      <div
        data-camera-position={cameraPosition.join(',')}
        data-camera-projection={cameraProjection}
        data-camera-target={cameraTarget.join(',')}
        data-explode-amount={explodeAmount}
        data-explode-step={explodeStepIndex ?? 'null'}
        data-fault-count={faultJoints.length}
        data-interactive-mode={interactiveMode}
        data-left-knee={formatAngle('left_knee_joint')}
        data-left-thigh-pitch={formatAngle('left_thigh_pitch_joint')}
        data-right-knee={formatAngle('right_knee_joint')}
        data-right-thigh-pitch={formatAngle('right_thigh_pitch_joint')}
        data-show-sub-parts={showSubParts}
        data-subpart-enabled={subPartEnabledNames.join(',')}
        data-testid="atom01-viewer"
      />
    )
  },
}))

vi.mock('@/components/Viewer3D', () => ({
  Atom01Viewer: viewerState.Atom01ViewerMock,
}))

vi.mock('@/components/Viewer3D/hooks/useAtom01AssemblyData', () => ({
  useAtom01AssemblyData: () => ({
    adapter: null,
    explodeManifest: assemblyState.explodeManifest,
    isLoading: false,
    error: null,
  }),
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

  afterEach(() => {
    vi.useRealTimers()
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

  it('stops the animation when resetting pose mid-playback', async () => {
    vi.useFakeTimers()
    render(<Atom01DemoPage />)

    const viewer = screen.getByTestId('atom01-viewer')
    const playButton = screen.getByRole('button', { name: 'play-circle 播放行走动画' })

    fireEvent.click(playButton)
    act(() => {
      vi.advanceTimersByTime(100)
    })

    expect(screen.getByRole('button', { name: 'pause-circle 暂停动画' })).toBeTruthy()
    expect(viewer.getAttribute('data-left-thigh-pitch')).not.toBe('0.00')

    fireEvent.click(screen.getByRole('button', { name: /重置姿态/i }))
    act(() => {
      vi.advanceTimersByTime(100)
    })

    expect(screen.getByRole('button', { name: 'play-circle 播放行走动画' })).toBeTruthy()
    expect(viewer.getAttribute('data-left-thigh-pitch')).toBe('0.00')
    expect(viewer.getAttribute('data-right-thigh-pitch')).toBe('0.00')
  })

  it('drives authored explode steps and service view into the viewer', async () => {
    const user = userEvent.setup()
    render(<Atom01DemoPage />)

    const viewer = screen.getByTestId('atom01-viewer')

    expect(viewer.getAttribute('data-camera-projection')).toBe('perspective')
    expect(viewer.getAttribute('data-explode-step')).toBe('null')
    expect(viewer.getAttribute('data-show-sub-parts')).toBe('false')

    await user.click(screen.getByRole('switch', { name: '准CAD拆解' }))
    await user.click(screen.getByRole('button', { name: '躯干维护视角' }))
    await user.click(screen.getByRole('button', { name: '下一步' }))

    expect(viewer.getAttribute('data-interactive-mode')).toBe('true')
    expect(viewer.getAttribute('data-camera-projection')).toBe('orthographic')
    expect(viewer.getAttribute('data-camera-position')).toBe('1.15,0.58,0.72')
    expect(viewer.getAttribute('data-camera-target')).toBe('0.04,0,0.28')
    expect(viewer.getAttribute('data-explode-step')).toBe('1')
    expect(viewer.getAttribute('data-explode-amount')).toBe('1')
    expect(viewer.getAttribute('data-show-sub-parts')).toBe('true')
    expect(viewer.getAttribute('data-subpart-enabled')).toBe('torso_link')
  })
})
