import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  buildAssemblyIndex,
  parseAssemblyManifest,
  parseExplodeManifest,
} from '@/components/Viewer3D/assemblyManifest'

function readJsonFromPublic(relativePath: string) {
  const currentDir = dirname(fileURLToPath(import.meta.url))
  const absolutePath = resolve(currentDir, '../../../../public', relativePath)
  return JSON.parse(readFileSync(absolutePath, 'utf-8')) as unknown
}

describe('assemblyManifest', () => {
  it('parses the static atom01 assembly manifest with required fields', () => {
    const rawManifest = readJsonFromPublic('models/robots/atom01/assembly_manifest.json')

    const manifest = parseAssemblyManifest(rawManifest)

    expect(manifest.robotId).toBe('atom01')
    expect(manifest.rootNodeId).toBe('base_link')
    expect(manifest.nodes.length).toBeGreaterThanOrEqual(8)
    expect(Object.keys(manifest.mesh_catalog).length).toBeGreaterThanOrEqual(8)
    expect(manifest.fastener_instances.length).toBeGreaterThanOrEqual(4)

    const index = buildAssemblyIndex(manifest)
    expect(index.byId.torso_link.display_name).toBe('躯干总成')
    expect(index.childrenByParent.torso_link).toEqual(
      expect.arrayContaining(['torso_shell_front', 'torso_shell_rear', 'left_arm_pitch_link', 'right_arm_pitch_link']),
    )
  })

  it('parses the static atom01 explode manifest with authored sequences', () => {
    const rawManifest = readJsonFromPublic('models/robots/atom01/explode_manifest.json')

    const manifest = parseExplodeManifest(rawManifest)

    expect(manifest.robotId).toBe('atom01')
    expect(manifest.views).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: 'torso_service_view',
        }),
      ]),
    )
    expect(manifest.sequences).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: 'torso_cover_removal',
          step_index: 1,
          node_ids: expect.arrayContaining(['torso_shell_front', 'torso_shell_rear']),
        }),
      ]),
    )
  })

  it('rejects manifests that omit required node transform fields', () => {
    expect(() =>
      parseAssemblyManifest({
        version: '2026-03-13',
        robotId: 'atom01',
        rootNodeId: 'base_link',
        mesh_catalog: {},
        nodes: [
          {
            id: 'broken-node',
            parent_id: null,
            children: [],
            mesh_id: 'base_link',
            display_name: 'Broken',
            category: 'link',
          },
        ],
        fastener_instances: [],
      }),
    ).toThrow('assembly node broken-node is missing transform')
  })
})
