import React, { Suspense, useMemo } from 'react'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'

import type { AssemblyTransform } from '@/components/Viewer3D/assemblyManifest'
import type { Atom01AssemblyAdapter } from '@/components/Viewer3D/hooks/useAtom01AssemblyData'

export interface AssemblyRenderItem {
  id: string
  parentId: string
  kind: 'node' | 'fastener'
  meshUrl: string
  translation: [number, number, number]
  rotationQuat: [number, number, number, number]
  scale: [number, number, number]
}

export interface Atom01AssemblyRendererProps {
  adapter: Atom01AssemblyAdapter
  rootLinkName: string
  baseOpacity?: number
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

export function collectAssemblyRenderItems(
  adapter: Atom01AssemblyAdapter,
  rootLinkName: string,
): AssemblyRenderItem[] {
  const items: AssemblyRenderItem[] = []
  const queue = [...(adapter.tree.nodes[rootLinkName]?.children ?? [])]

  while (queue.length > 0) {
    const currentId = queue.shift()
    if (!currentId) continue

    const node = adapter.tree.nodes[currentId]
    const transform = getTransform(adapter, currentId)
    const meshUrl = node?.runtimeAssetPaths[0]

    if (node && transform && meshUrl) {
      items.push({
        id: currentId,
        parentId: node.parentId ?? rootLinkName,
        kind: 'node',
        meshUrl,
        translation: transform.translation,
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
          data-translation={formatVector(item.translation)}
          position={item.translation}
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
}) => {
  const itemsByParent = useMemo(() => {
    return collectAssemblyRenderItems(adapter, rootLinkName).reduce<Record<string, AssemblyRenderItem[]>>((acc, item) => {
      acc[item.parentId] = acc[item.parentId] ? [...acc[item.parentId], item] : [item]
      return acc
    }, {})
  }, [adapter, rootLinkName])

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
