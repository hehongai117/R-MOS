import { Box3, Object3D, Vector3 } from 'three'

import type { CameraPreset } from '@/components/Viewer3D/assemblyTree'

export interface VisibleBounds {
  center: [number, number, number]
  radius: number
}

export function centerObjectAtOrigin<T extends Object3D>(object: T): {
  object: T
  bounds: VisibleBounds | null
} {
  const box = new Box3().setFromObject(object)
  if (box.isEmpty()) {
    return { object, bounds: null }
  }

  const center = box.getCenter(new Vector3())
  const size = box.getSize(new Vector3())
  const radius = Math.max(size.x, size.y, size.z) * 0.5
  if (!Number.isFinite(radius) || radius <= 0) {
    return { object, bounds: null }
  }

  object.position.sub(center)

  return {
    object,
    bounds: {
      center: [0, 0, 0],
      radius,
    },
  }
}

export function buildAutoCameraPreset(
  bounds: VisibleBounds,
  options: {
    mode: 'overview' | 'isolated' | 'runtime'
    fullscreen: boolean
    emphasis?: 'torso' | 'upper-limb' | 'default'
  },
): CameraPreset {
  const [cx, cy, cz] = bounds.center
  const radius = Math.max(bounds.radius, 0.08)

  if (options.mode === 'runtime') {
    const distance = Math.min(Math.max(radius * (options.fullscreen ? 2.2 : 2.45), 0.7), 4.2)
    return {
      position: [cx + distance, cy + distance * 0.52, cz + distance * 1.08],
      target: [cx, cy, cz],
      fov: 46,
    }
  }

  if (options.mode === 'overview') {
    const distance = Math.min(Math.max(radius * (options.fullscreen ? 2.5 : 2.8), 1.25), 4.4)
    return {
      position: [cx + distance, cy + distance * 0.6, cz + distance * 1.12],
      target: [cx, cy, cz],
      fov: 48,
    }
  }

  const emphasis = options.emphasis ?? 'default'
  const distanceFactor = emphasis === 'torso'
    ? (options.fullscreen ? 2.2 : 2.45)
    : emphasis === 'upper-limb'
      ? (options.fullscreen ? 1.95 : 2.15)
      : (options.fullscreen ? 1.6 : 1.85)
  const maxDistance = emphasis === 'torso' ? 2.5 : emphasis === 'upper-limb' ? 2.0 : 1.8
  const distance = Math.min(Math.max(radius * distanceFactor, 0.42), maxDistance)

  return {
    position: [cx + distance, cy + distance * 0.45, cz + distance * 0.88],
    target: [cx, cy, cz],
    fov: emphasis === 'torso' ? 52 : 48,
  }
}
