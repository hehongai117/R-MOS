import { useRef, useMemo, useCallback, Component, type ReactNode } from 'react'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import type { ThreeEvent } from '@react-three/fiber'
import type { AssemblyNode, AssemblyManifest } from './assemblyManifest'
import type { AssemblyJoint } from './useAssemblyManifest'
import { buildPartMetadata, type PartInfo } from './manifestPartMetadata'

/** Catch GLB load failures silently. */
class MeshErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() { return this.state.hasError ? null : this.props.children }
}

export type { PartInfo }

export interface InteractiveManifestViewerProps {
  manifest: AssemblyManifest & { joints?: AssemblyJoint[] }
  robotId: number
  onPartHover?: (part: PartInfo | null) => void
  onPartSelect?: (part: PartInfo | null) => void
  onPartDoubleClick?: (part: PartInfo) => void
  hoveredPart?: string | null
  selectedPart?: string | null
  highlightLinks?: string[]
  fadedPartNames?: string[]
  fadeOpacity?: number
  visiblePartNames?: string[]
  clickablePartNames?: string[]
  explodeDistance?: number
  jointAngles?: Record<string, number>
}

export function InteractiveManifestViewer({
  manifest,
  robotId,
  onPartHover,
  onPartSelect,
  onPartDoubleClick,
  hoveredPart,
  selectedPart,
  highlightLinks = [],
  fadedPartNames = [],
  fadeOpacity = 0.15,
  visiblePartNames,
  clickablePartNames,
  explodeDistance = 0,
  jointAngles = {},
}: InteractiveManifestViewerProps) {
  const { nodeMap, jointByChild, partMetadata } = useMemo(() => {
    const nMap = new Map<string, AssemblyNode>()
    manifest.nodes.forEach((n) => nMap.set(n.id, n))

    const jMap = new Map<string, { axis: [number, number, number] }>()
    if (manifest.joints) {
      manifest.joints.forEach((j) => {
        jMap.set(j.child_link, { axis: j.axis })
      })
    }

    const meta = buildPartMetadata(manifest)
    return { nodeMap: nMap, jointByChild: jMap, partMetadata: meta }
  }, [manifest])

  const rootNode = nodeMap.get(manifest.rootNodeId)
  if (!rootNode) return null

  return (
    <group rotation={[-Math.PI / 2, 0, 0]}>
      <InteractiveNodeGroup
        node={rootNode}
        nodeMap={nodeMap}
        manifest={manifest}
        robotId={robotId}
        jointAngles={jointAngles}
        jointByChild={jointByChild}
        partMetadata={partMetadata}
        onPartHover={onPartHover}
        onPartSelect={onPartSelect}
        onPartDoubleClick={onPartDoubleClick}
        hoveredPart={hoveredPart ?? null}
        selectedPart={selectedPart ?? null}
        highlightLinks={highlightLinks}
        fadedPartNames={fadedPartNames}
        fadeOpacity={fadeOpacity}
        visiblePartNames={visiblePartNames}
        clickablePartNames={clickablePartNames}
        explodeDistance={explodeDistance}
      />
    </group>
  )
}

interface InteractiveNodeGroupProps {
  node: AssemblyNode
  nodeMap: Map<string, AssemblyNode>
  manifest: AssemblyManifest
  robotId: number
  jointAngles: Record<string, number>
  jointByChild: Map<string, { axis: [number, number, number] }>
  partMetadata: Record<string, PartInfo>
  onPartHover?: (part: PartInfo | null) => void
  onPartSelect?: (part: PartInfo | null) => void
  onPartDoubleClick?: (part: PartInfo) => void
  hoveredPart: string | null
  selectedPart: string | null
  highlightLinks: string[]
  fadedPartNames: string[]
  fadeOpacity: number
  visiblePartNames?: string[]
  clickablePartNames?: string[]
  explodeDistance: number
}

function InteractiveNodeGroup({
  node, nodeMap, manifest, robotId, jointAngles, jointByChild,
  partMetadata, onPartHover, onPartSelect, onPartDoubleClick,
  hoveredPart, selectedPart, highlightLinks, fadedPartNames,
  fadeOpacity, visiblePartNames, clickablePartNames, explodeDistance,
}: InteractiveNodeGroupProps) {
  const groupRef = useRef<THREE.Group>(null)

  // Check visibility — if this node has a mesh and is not in visiblePartNames, hide just the mesh
  // but still render children (they may be visible)
  const hasMesh = !!(node.mesh_id && manifest.mesh_catalog[node.mesh_id])
  const meshVisible = !visiblePartNames || visiblePartNames.includes(node.id)

  const { translation, rotation_quat, scale } = node.transform
  const position: [number, number, number] = translation

  const quaternion = useMemo(() => {
    const q = new THREE.Quaternion(
      rotation_quat[0], rotation_quat[1], rotation_quat[2], rotation_quat[3],
    )
    const jointInfo = jointByChild.get(node.id)
    const jointAngle = node.link_name ? (jointAngles[node.link_name] ?? 0) : 0
    if (jointInfo && jointAngle !== 0) {
      const axisVec = new THREE.Vector3(...jointInfo.axis).normalize()
      const jointQuat = new THREE.Quaternion().setFromAxisAngle(axisVec, jointAngle)
      q.multiply(jointQuat)
    }
    return q
  }, [rotation_quat, jointByChild, node.id, node.link_name, jointAngles])

  const explodedPosition: [number, number, number] = explodeDistance > 0
    ? [
        position[0] * (1 + explodeDistance),
        position[1] * (1 + explodeDistance),
        position[2] * (1 + explodeDistance),
      ]
    : position

  // Visual state
  const isSelected = selectedPart === node.id
  const isHovered = hoveredPart === node.id
  const isHighlighted = highlightLinks.includes(node.id)
  const isFaded = fadedPartNames.includes(node.id)
  const isClickable = !clickablePartNames || clickablePartNames.includes(node.id)
  const partInfo = partMetadata[node.id]

  return (
    <group
      ref={groupRef}
      position={explodedPosition}
      quaternion={quaternion}
      scale={scale}
    >
      {hasMesh && meshVisible && (
        <MeshErrorBoundary>
          <InteractiveLinkMesh
            meshPath={manifest.mesh_catalog[node.mesh_id!]}
            robotId={robotId}
            isSelected={isSelected}
            isHovered={isHovered}
            isHighlighted={isHighlighted}
            isFaded={isFaded}
            fadeOpacity={fadeOpacity}
            isClickable={isClickable}
            partInfo={partInfo ?? null}
            onPartHover={onPartHover}
            onPartSelect={onPartSelect}
            onPartDoubleClick={onPartDoubleClick}
            selectedPart={selectedPart}
          />
        </MeshErrorBoundary>
      )}
      {node.children.map((childId) => {
        const childNode = nodeMap.get(childId)
        if (!childNode) return null
        return (
          <InteractiveNodeGroup
            key={childId}
            node={childNode}
            nodeMap={nodeMap}
            manifest={manifest}
            robotId={robotId}
            jointAngles={jointAngles}
            jointByChild={jointByChild}
            partMetadata={partMetadata}
            onPartHover={onPartHover}
            onPartSelect={onPartSelect}
            onPartDoubleClick={onPartDoubleClick}
            hoveredPart={hoveredPart}
            selectedPart={selectedPart}
            highlightLinks={highlightLinks}
            fadedPartNames={fadedPartNames}
            fadeOpacity={fadeOpacity}
            visiblePartNames={visiblePartNames}
            clickablePartNames={clickablePartNames}
            explodeDistance={explodeDistance}
          />
        )
      })}
    </group>
  )
}

function InteractiveLinkMesh({
  meshPath, robotId,
  isSelected, isHovered, isHighlighted, isFaded, fadeOpacity,
  isClickable, partInfo,
  onPartHover, onPartSelect, onPartDoubleClick, selectedPart,
}: {
  meshPath: string
  robotId: number
  isSelected: boolean
  isHovered: boolean
  isHighlighted: boolean
  isFaded: boolean
  fadeOpacity: number
  isClickable: boolean
  partInfo: PartInfo | null
  onPartHover?: (part: PartInfo | null) => void
  onPartSelect?: (part: PartInfo | null) => void
  onPartDoubleClick?: (part: PartInfo) => void
  selectedPart: string | null
}) {
  const url = `/api/v1/robots/${robotId}/assets/${meshPath}`
  const { scene } = useGLTF(url)

  const cloned = useMemo(() => {
    const clone = scene.clone(true)
    clone.traverse((child) => {
      if (!(child as THREE.Mesh).isMesh) return
      const mesh = child as THREE.Mesh

      if (isSelected) {
        mesh.material = new THREE.MeshStandardMaterial({
          color: 0x00d4ff,
          emissive: 0x00d4ff,
          emissiveIntensity: 0.4,
        })
      } else if (isHovered) {
        mesh.material = new THREE.MeshStandardMaterial({
          color: 0x80e8ff,
          emissive: 0x80e8ff,
          emissiveIntensity: 0.2,
        })
      } else if (isHighlighted) {
        mesh.material = new THREE.MeshStandardMaterial({
          color: 0x00d084,
          emissive: 0x00d084,
          emissiveIntensity: 0.3,
        })
      } else if (isFaded) {
        mesh.material = new THREE.MeshStandardMaterial({
          color: 0x888899,
          transparent: true,
          opacity: fadeOpacity,
          depthWrite: false,
        })
      } else {
        if (!mesh.material || (mesh.material as THREE.MeshStandardMaterial).color === undefined) {
          mesh.material = new THREE.MeshStandardMaterial({ color: 0x888899 })
        }
      }
    })
    return clone
  }, [scene, isSelected, isHovered, isHighlighted, isFaded, fadeOpacity])

  const handlePointerOver = useCallback((e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    if (partInfo && onPartHover) onPartHover(partInfo)
  }, [partInfo, onPartHover])

  const handlePointerOut = useCallback((e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    if (onPartHover) onPartHover(null)
  }, [onPartHover])

  const handleClick = useCallback((e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    if (!isClickable || !partInfo || !onPartSelect) return
    // Toggle: if already selected, deselect
    if (selectedPart === partInfo.name) {
      onPartSelect(null)
    } else {
      onPartSelect(partInfo)
    }
  }, [isClickable, partInfo, onPartSelect, selectedPart])

  const handleDoubleClick = useCallback((e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    if (partInfo && onPartDoubleClick) onPartDoubleClick(partInfo)
  }, [partInfo, onPartDoubleClick])

  return (
    <primitive
      object={cloned}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
    />
  )
}
