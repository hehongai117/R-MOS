import React, { Suspense, useMemo } from 'react'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'

import type { AssemblyTransform, ExplodeManifest } from '@/components/Viewer3D/assemblyManifest'
import type { Atom01AssemblyAdapter } from '@/components/Viewer3D/hooks/useAtom01AssemblyData'

export interface AssemblyRenderItem {
  id: string
  parentId: string
  kind: 'node' | 'fastener'
  meshUrl: string
  translation: [number, number, number]
  renderTranslation: [number, number, number]
  rotationQuat: [number, number, number, number]
  scale: [number, number, number]
}

export interface Atom01AssemblyRendererProps {
  adapter: Atom01AssemblyAdapter
  rootLinkName: string
  baseOpacity?: number
  explodeManifest?: ExplodeManifest | null
  explodeAmount?: number
  explodeStepIndex?: number | null
}

function formatVector(value: [number, number, number]) {
  return value.join(',')
}

function getTransform(
  adapter: Atom01AssemblyAdapter,
  id: string,
): AssemblyTransform | null {
  return adapter.transforms[id] ?? null
}

function buildExplodeOffsetMap(
  explodeManifest: ExplodeManifest | null | undefined,
  rootLinkName: string,
  explodeAmount: number,
  explodeStepIndex: number | null,
): Record<string, [number, number, number]> {
  if (!explodeManifest || explodeAmount <= 0) {
    return {}
  }

  const anchoredSequences = explodeManifest.sequences.filter(
    (sequence) => sequence.anchor_node_id === rootLinkName,
  )
  const activeStepIndex = explodeStepIndex ?? anchoredSequences.reduce<number | null>((lowest, sequence) => {
    if (lowest == null || sequence.step_index < lowest) {
      return sequence.step_index
    }
    return lowest
  }, null)

  return anchoredSequences.reduce<Record<string, [number, number, number]>>((acc, sequence) => {
    if (activeStepIndex != null && sequence.step_index > activeStepIndex) {
      return acc
    }

    const offset: [number, number, number] = [
      sequence.direction[0] * sequence.distance * explodeAmount,
      sequence.direction[1] * sequence.distance * explodeAmount,
      sequence.direction[2] * sequence.distance * explodeAmount,
    ]

    sequence.node_ids.forEach((nodeId) => {
      const current = acc[nodeId] ?? [0, 0, 0]
      acc[nodeId] = [
        current[0] + offset[0],
        current[1] + offset[1],
        current[2] + offset[2],
      ]
    })

    return acc
  }, {})
}

export function collectAssemblyRenderItems(
  adapter: Atom01AssemblyAdapter,
  rootLinkName: string,
  explodeManifest?: ExplodeManifest | null,
  explodeAmount = 0,
  explodeStepIndex: number | null = null,
): AssemblyRenderItem[] {
  const items: AssemblyRenderItem[] = []
  const queue = [...(adapter.tree.nodes[rootLinkName]?.children ?? [])]
  const explodeOffsetMap = buildExplodeOffsetMap(
    explodeManifest,
    rootLinkName,
    explodeAmount,
    explodeStepIndex,
  )

  while (queue.length > 0) {
    const currentId = queue.shift()
    if (!currentId) continue

    const node = adapter.tree.nodes[currentId]
    const transform = getTransform(adapter, currentId)
    const meshUrl = node?.runtimeAssetPaths[0]

    if (node && transform && meshUrl) {
      const explodeOffset = explodeOffsetMap[currentId] ?? [0, 0, 0]
      items.push({
        id: currentId,
        parentId: node.parentId ?? rootLinkName,
        kind: 'node',
        meshUrl,
        translation: transform.translation,
        renderTranslation: [
          transform.translation[0] + explodeOffset[0],
          transform.translation[1] + explodeOffset[1],
          transform.translation[2] + explodeOffset[2],
        ],
        rotationQuat: transform.rotation_quat,
        scale: transform.scale,
      })
    }

    queue.push(...(node?.children ?? []))
  }

  adapter.fastenerInstances.forEach((fastener) => {
    const transform = getTransform(adapter, fastener.id)
    const meshUrl = adapter.meshCatalog[fastener.mesh_id]
    if (!transform || !meshUrl) return

    let currentParent: string | null = fastener.parent_id
    let belongsToRoot = false
    while (currentParent) {
      if (currentParent === rootLinkName) {
        belongsToRoot = true
        break
      }
      currentParent = adapter.tree.nodes[currentParent]?.parentId ?? null
    }
    if (!belongsToRoot) return

    items.push({
      id: fastener.id,
      parentId: fastener.parent_id,
      kind: 'fastener',
      meshUrl,
      translation: transform.translation,
      renderTranslation: transform.translation,
      rotationQuat: transform.rotation_quat,
      scale: transform.scale,
    })
  })

  return items
}

const AssemblyMesh: React.FC<{ meshUrl: string; opacity: number }> = ({ meshUrl, opacity }) => {
  const { scene } = useGLTF(meshUrl)
  const clonedScene = useMemo(() => {
    const cloned = scene.clone()
    cloned.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh
        const material = mesh.material
        if (material) {
          mesh.material = (material as THREE.Material).clone()
          const standardMaterial = mesh.material as THREE.MeshStandardMaterial
          standardMaterial.transparent = opacity < 1
          standardMaterial.opacity = opacity
          standardMaterial.depthWrite = opacity > 0.5
        }
      }
    })
    return cloned
  }, [opacity, scene])

  return <primitive object={clonedScene} />
}

const AssemblyBranch: React.FC<{
  adapter: Atom01AssemblyAdapter
  parentId: string
  itemsByParent: Record<string, AssemblyRenderItem[]>
  baseOpacity: number
}> = ({ adapter, parentId, itemsByParent, baseOpacity }) => {
  const items = itemsByParent[parentId] ?? []

  return (
    <>
      {items.map((item) => (
        <group
          key={item.id}
          data-kind={item.kind}
          data-parent-id={item.parentId}
          data-testid={item.kind === 'fastener' ? `assembly-fastener-${item.id}` : `assembly-node-${item.id}`}
          data-translation={formatVector(item.renderTranslation)}
          position={item.renderTranslation}
          quaternion={item.rotationQuat}
          scale={item.scale}
        >
          <Suspense fallback={null}>
            <AssemblyMesh meshUrl={item.meshUrl} opacity={baseOpacity} />
          </Suspense>
          {item.kind === 'node' && adapter.tree.nodes[item.id] ? (
            <AssemblyBranch
              adapter={adapter}
              parentId={item.id}
              itemsByParent={itemsByParent}
              baseOpacity={baseOpacity}
            />
          ) : null}
        </group>
      ))}
    </>
  )
}

export const Atom01AssemblyRenderer: React.FC<Atom01AssemblyRendererProps> = ({
  adapter,
  rootLinkName,
  baseOpacity = 0.85,
  explodeManifest = null,
  explodeAmount = 0,
  explodeStepIndex = null,
}) => {
  const renderItems = useMemo(() => {
    return collectAssemblyRenderItems(
      adapter,
      rootLinkName,
      explodeManifest,
      explodeAmount,
      explodeStepIndex,
    )
  }, [adapter, explodeAmount, explodeManifest, explodeStepIndex, rootLinkName])

  const itemsByParent = useMemo(() => {
    return renderItems.reduce<Record<string, AssemblyRenderItem[]>>((acc, item) => {
      acc[item.parentId] = acc[item.parentId] ? [...acc[item.parentId], item] : [item]
      return acc
    }, {})
  }, [renderItems])

  if (!adapter.tree.nodes[rootLinkName]) {
    return null
  }

  return (
    <group data-testid={`assembly-root-${rootLinkName}`}>
      <AssemblyBranch
        adapter={adapter}
        parentId={rootLinkName}
        itemsByParent={itemsByParent}
        baseOpacity={baseOpacity}
      />
    </group>
  )
}

export default Atom01AssemblyRenderer
