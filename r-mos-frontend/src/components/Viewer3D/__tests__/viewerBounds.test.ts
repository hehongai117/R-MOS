import { BoxGeometry, Mesh, MeshBasicMaterial } from 'three'
import { describe, expect, it } from 'vitest'

import { buildAutoCameraPreset, centerObjectAtOrigin } from '@/components/Viewer3D/viewerBounds'

describe('viewerBounds', () => {
  it('recenters offset objects at the origin while preserving radius', () => {
    const mesh = new Mesh(new BoxGeometry(2, 4, 6), new MeshBasicMaterial())
    mesh.position.set(5, 2, -1)

    const result = centerObjectAtOrigin(mesh)

    expect(result.bounds).toEqual({
      center: [0, 0, 0],
      radius: 3,
    })
    expect(mesh.position.toArray()).toEqual([0, 0, 0])
  })

  it('builds a camera preset targeting the model center', () => {
    const preset = buildAutoCameraPreset(
      {
        center: [1, 2, 3],
        radius: 0.5,
      },
      {
        mode: 'runtime',
        fullscreen: false,
      },
    )

    expect(preset.target).toEqual([1, 2, 3])
    expect(preset.position[0]).toBeGreaterThan(1)
    expect(preset.position[1]).toBeGreaterThan(2)
    expect(preset.position[2]).toBeGreaterThan(3)
    expect(preset.fov).toBe(46)
  })
})
