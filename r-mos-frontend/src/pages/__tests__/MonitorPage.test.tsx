import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { reconnectMock, useWebSocketMock } = vi.hoisted(() => ({
  reconnectMock: vi.fn(),
  useWebSocketMock: vi.fn(),
}))

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: useWebSocketMock,
}))

vi.mock('@/components/Viewer3D/Atom01Viewer', () => ({
  default: ({
    jointAngles = {},
    faultJoints = [],
    highlightLinks = [],
  }: {
    jointAngles?: Record<string, number>
    faultJoints?: string[]
    highlightLinks?: string[]
  }) => (
    <div
      data-fault-joints={faultJoints.join(',')}
      data-highlight-links={highlightLinks.join(',')}
      data-joint-count={Object.keys(jointAngles).length}
      data-right-knee={jointAngles.right_knee_joint?.toFixed(4) ?? 'unset'}
      data-testid="atom01-monitor-viewer"
    />
  ),
}))

import MonitorPage from '@/pages/MonitorPage'

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

describe('MonitorPage', () => {
  beforeEach(() => {
    reconnectMock.mockReset()
    useWebSocketMock.mockReset().mockReturnValue({
      isConnected: true,
      telemetryData: {
        sensors: {
          battery: 18,
          temperature: 67,
          imu: {
            acceleration: {
              x: 1.234,
              y: 2.345,
              z: 3.456,
            },
            angular_velocity: {
              x: 0.123,
              y: 0.234,
              z: 0.345,
            },
          },
          voltage: {
            main_bus: 48.6,
            servo_bus: 24.2,
          },
          pressure: {
            left_foot: 128.4,
          },
        },
        joints: [
          {
            joint_id: 'knee_right',
            position: 0.1234,
            velocity: 0.02,
            torque: 5.2,
            current: 2.1,
            temperature: 54.3,
            error_code: 'E002_STALL',
          },
          {
            joint_id: 'hip_left',
            position: -0.3421,
            velocity: 0.12,
            torque: 4.1,
            current: 1.9,
            temperature: 46.7,
          },
          {
            joint_id: 'shoulder_right',
            position: 0.4567,
            velocity: 0.08,
            torque: 2.8,
            current: 1.1,
            temperature: 43.5,
          },
        ],
        active_faults: ['E002_STALL'],
      },
      error: null,
      status: 'connected',
      isDataStale: false,
      retryCount: 0,
      lastUpdateTime: new Date('2026-03-12T17:30:00.000Z'),
      reconnect: reconnectMock,
    })
  })

  it('renders monitor dashboard sections and passes mapped telemetry to the atom01 viewer', () => {
    render(<MonitorPage />)

    expect(screen.getByText('REALTIME MONITOR')).toBeTruthy()
    expect(screen.getByRole('heading', { name: '实时监控' })).toBeTruthy()
    expect(screen.getByText('机器人态势')).toBeTruthy()
    expect(screen.getByText('姿态与运动')).toBeTruthy()
    expect(screen.getByText('电源与载荷')).toBeTruthy()
    expect(screen.getByText('重点关节')).toBeTruthy()
    expect(screen.getByText('故障定位')).toBeTruthy()
    expect(screen.getAllByText('右膝关节').length).toBeGreaterThan(0)
    expect(screen.getAllByText('左髋关节').length).toBeGreaterThan(0)

    const viewer = screen.getByTestId('atom01-monitor-viewer')
    expect(viewer.getAttribute('data-right-knee')).toBe('0.1234')
    expect(viewer.getAttribute('data-fault-joints')).toContain('right_knee_joint')
    expect(viewer.getAttribute('data-highlight-links')).toContain('right_knee_link')
    expect(Number(viewer.getAttribute('data-joint-count'))).toBeGreaterThan(0)
  })

  it('renders reconnect action for failed status', () => {
    useWebSocketMock.mockReturnValue({
      isConnected: false,
      telemetryData: null,
      error: '机器人适配器不可用',
      status: 'failed',
      isDataStale: false,
      retryCount: 3,
      lastUpdateTime: null,
      reconnect: reconnectMock,
    })

    render(<MonitorPage />)

    expect(screen.getByRole('button', { name: '重连' })).toBeTruthy()
    expect(screen.getByText('机器人适配器不可用')).toBeTruthy()
  })

  it('calls reconnect when reconnect button is clicked', () => {
    useWebSocketMock.mockReturnValue({
      isConnected: false,
      telemetryData: null,
      error: '机器人适配器不可用',
      status: 'failed',
      isDataStale: false,
      retryCount: 3,
      lastUpdateTime: null,
      reconnect: reconnectMock,
    })

    render(<MonitorPage />)

    fireEvent.click(screen.getByRole('button', { name: '重连' }))

    expect(reconnectMock).toHaveBeenCalledTimes(1)
  })
})
