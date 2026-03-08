import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { reconnectMock, useWebSocketMock } = vi.hoisted(() => ({
  reconnectMock: vi.fn(),
  useWebSocketMock: vi.fn(),
}))

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: useWebSocketMock,
}))

vi.mock('@/components/Viewer3D/RobotViewer', () => ({
  default: ({ height }: { height: number }) => <div>RobotViewer height={height}</div>,
}))

vi.mock('@/components/common/ErrorBoundary', () => ({
  Viewer3DErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
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
      isConnected: false,
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
          },
        },
        joints: [
          {
            joint_id: 'J1',
            position: 0.1234,
            velocity: 0,
            torque: 0.1,
            error_code: 'E002_STALL',
          },
        ],
        active_faults: ['E002_STALL'],
      },
      error: '机器人适配器不可用',
      status: 'failed',
      isDataStale: false,
      retryCount: 3,
      reconnect: reconnectMock,
    })
  })

  it('renders industrial monitor header and reconnect action for failed status', () => {
    render(<MonitorPage />)

    expect(screen.getByText('REALTIME MONITOR')).toBeTruthy()
    expect(screen.getByRole('heading', { name: '实时监控' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '重连' })).toBeTruthy()
    expect(screen.getByText('机器人适配器不可用')).toBeTruthy()
  })

  it('renders telemetry sections and joint error details', () => {
    render(<MonitorPage />)

    expect(screen.getByText('BATTERY')).toBeTruthy()
    expect(screen.getAllByText('ACTIVE FAULTS').length).toBeGreaterThan(0)
    expect(screen.getByText('SYS TEMP')).toBeTruthy()
    expect(screen.getByText('IMU ACCELERATION')).toBeTruthy()
    expect(screen.getByText('JOINT STATUS')).toBeTruthy()
    expect(screen.getByText('18')).toBeTruthy()
    expect(screen.getByText('67')).toBeTruthy()
    expect(screen.getAllByText('E002_STALL').length).toBeGreaterThan(0)
    expect(screen.getByText('0.1234')).toBeTruthy()
  })

  it('calls reconnect when reconnect button is clicked', () => {
    render(<MonitorPage />)

    fireEvent.click(screen.getByRole('button', { name: '重连' }))

    expect(reconnectMock).toHaveBeenCalledTimes(1)
  })
})
