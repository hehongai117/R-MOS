import { describe, expect, it } from 'vitest'

import { mapTelemetryMessageToRobotData } from '../useRobotData'

describe('mapTelemetryMessageToRobotData', () => {
  it('maps the unified telemetry websocket payload to Viewer3D state', () => {
    const result = mapTelemetryMessageToRobotData({
      type: 'telemetry',
      timestamp: '2026-03-08T10:00:00Z',
      payload: {
        joints: [{ joint_id: 'waist', position: 1.2, velocity: 0.4, torque: 0.8, temperature: 54 }],
        sensors: { battery: 82, temperature: 43 },
        active_faults: ['E002_STALL'],
      },
    })

    expect(result).toEqual({
      joints: [{ joint_id: 'waist', position: 1.2, velocity: 0.4, torque: 0.8, temperature: 54 }],
      sensors: { battery: 82, temperature: 43 },
      faults: ['E002_STALL'],
      timestamp: '2026-03-08T10:00:00Z',
    })
  })
})
