import { useRef, useMemo, Component, type ReactNode } from 'react'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import type { AssemblyNode, AssemblyManifest } from './assemblyManifest'
import type { AssemblyJoint } from './useAssemblyManifest'

/** Catch GLB load failures silently — render nothing instead of crashing. */
class MeshErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() { return this.state.hasError ? null : this.props.children }
}

interface ManifestDrivenRendererProps {
  manifest: AssemblyManifest & { joints?: AssemblyJoint[] }
  robotId: number
  jointAngles?: Record<string, number>
  highlightLinks?: string[]
  explodeDistance?: number
}

/**
 * Recursively render the assembly tree from manifest nodes.
 * Each node creates a <group> with its transform applied.
 * Meshes are loaded on-demand via useGLTF.
 */
export function ManifestDrivenRenderer({
  manifest,
  robotId,
  jointAngles = {},
  highlightLinks = [],
  explodeDistance = 0,
}: ManifestDrivenRendererProps) {
  // Build lookup maps
  const { nodeMap, jointByChild } = useMemo(() => {
    const nMap = new Map<string, AssemblyNode>()
    manifest.nodes.forEach((n) => nMap.set(n.id, n))

    const jMap = new Map<string, { axis: [number, number, number] }>()
    if (manifest.joints) {
      manifest.joints.forEach((j) => {
        jMap.set(j.child_link, { axis: j.axis })
      })
    }
    return { nodeMap: nMap, jointByChild: jMap }
  }, [manifest])

  const rootNode = nodeMap.get(manifest.rootNodeId)
  if (!rootNode) return null

  return (
    <group rotation={[-Math.PI / 2, 0, 0]}>
      <AssemblyNodeGroup
        node={rootNode}
        nodeMap={nodeMap}
        manifest={manifest}
        robotId={robotId}
        jointAngles={jointAngles}
        jointByChild={jointByChild}
        highlightLinks={highlightLinks}
        explodeDistance={explodeDistance}
      />
    </group>
  )
}

interface AssemblyNodeGroupProps {
  node: AssemblyNode
  nodeMap: Map<string, AssemblyNode>
  manifest: AssemblyManifest
  robotId: number
  jointAngles: Record<string, number>
  jointByChild: Map<string, { axis: [number, number, number] }>
  highlightLinks: string[]
  explodeDistance: number
}

function AssemblyNodeGroup({
  node,
  nodeMap,
  manifest,
  robotId,
  jointAngles,
  jointByChild,
  highlightLinks,
  explodeDistance,
}: AssemblyNodeGroupProps) {
  const groupRef = useRef<THREE.Group>(null)

  // Apply transform
  const { translation, rotation_quat, scale } = node.transform
  const position: [number, number, number] = translation

  const quaternion = useMemo(() => {
    const q = new THREE.Quaternion(
      rotation_quat[0], rotation_quat[1], rotation_quat[2], rotation_quat[3]
    )

    // Apply joint rotation if this link has a joint
    const jointInfo = jointByChild.get(node.id)
    const jointAngle = node.link_name ? (jointAngles[node.link_name] ?? 0) : 0
    if (jointInfo && jointAngle !== 0) {
      const axisVec = new THREE.Vector3(...jointInfo.axis).normalize()
      const jointQuat = new THREE.Quaternion().setFromAxisAngle(axisVec, jointAngle)
      q.multiply(jointQuat)
    }

    return q
  }, [rotation_quat, jointByChild, node.id, node.link_name, jointAngles])

  // Explode: push node along its position vector
  const explodedPosition: [number, number, number] = explodeDistance > 0
    ? [
        position[0] * (1 + explodeDistance),
        position[1] * (1 + explodeDistance),
        position[2] * (1 + explodeDistance),
      ]
    : position

  const isHighlighted = highlightLinks.includes(node.id)

  return (
    <group
      ref={groupRef}
      position={explodedPosition}
      quaternion={quaternion}
      scale={scale}
    >
      {node.mesh_id && manifest.mesh_catalog[node.mesh_id] && (
        <MeshErrorBoundary>
          <LinkMesh
            meshPath={manifest.mesh_catalog[node.mesh_id]}
            robotId={robotId}
            highlighted={isHighlighted}
          />
        </MeshErrorBoundary>
      )}
      {node.children.map((childId) => {
        const childNode = nodeMap.get(childId)
        if (!childNode) return null
        return (
          <AssemblyNodeGroup
            key={childId}
            node={childNode}
            nodeMap={nodeMap}
            manifest={manifest}
            robotId={robotId}
            jointAngles={jointAngles}
            jointByChild={jointByChild}
            highlightLinks={highlightLinks}
            explodeDistance={explodeDistance}
          />
        )
      })}
    </group>
  )
}

function LinkMesh({
  meshPath,
  robotId,
  highlighted,
}: {
  meshPath: string
  robotId: number
  highlighted: boolean
}) {
  const url = `/api/v1/robots/${robotId}/assets/${meshPath}`
  const { scene } = useGLTF(url)

  const cloned = useMemo(() => {
    const clone = scene.clone(true)
    clone.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh
        if (highlighted) {
          mesh.material = new THREE.MeshStandardMaterial({
            color: 0x00d084,
            emissive: 0x00d084,
            emissiveIntensity: 0.3,
          })
        } else {
          // Default material if none
          if (!mesh.material || (mesh.material as THREE.MeshStandardMaterial).color === undefined) {
            mesh.material = new THREE.MeshStandardMaterial({ color: 0x888899 })
          }
        }
      }
    })
    return clone
  }, [scene, highlighted])

  return <primitive object={cloned} />
}
