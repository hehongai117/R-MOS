import type { AssemblyManifest, AssemblyNode } from './assemblyManifest'

/**
 * PartInfo interface — matches the one in Atom01Interactive.tsx.
 * Re-exported here so consumers don't need to import from the legacy file.
 */
export interface PartInfo {
  name: string
  displayName: string
  group: string
  jointName?: string
}

/** Infer a human-readable group from the node id / link_name. */
function inferGroup(nodeId: string): string {
  const id = nodeId.toLowerCase()
  if (id.includes('left_arm') || id.includes('left_shoulder') || id.includes('left_elbow') || id.includes('left_wrist')) return 'left_arm'
  if (id.includes('right_arm') || id.includes('right_shoulder') || id.includes('right_elbow') || id.includes('right_wrist')) return 'right_arm'
  if (id.includes('left_thigh') || id.includes('left_knee') || id.includes('left_ankle') || id.includes('left_shank') || id.includes('left_hip')) return 'left_leg'
  if (id.includes('right_thigh') || id.includes('right_knee') || id.includes('right_ankle') || id.includes('right_shank') || id.includes('right_hip')) return 'right_leg'
  if (id.includes('torso') || id.includes('waist') || id.includes('trunk')) return 'torso'
  return 'base'
}

/** Convert snake_case id to Title Case display name. */
function idToDisplayName(id: string): string {
  return id
    .replace(/_link$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Build a PartInfo record from an assembly manifest.
 * Works with both full manifests (with display_name/category) and minimal ones.
 */
export function buildPartMetadata(
  manifest: AssemblyManifest & { joints?: Array<{ name: string; child_link: string }> },
): Record<string, PartInfo> {
  const jointByChild = new Map<string, string>()
  if (manifest.joints) {
    for (const j of manifest.joints) {
      jointByChild.set(j.child_link, j.name)
    }
  }

  const metadata: Record<string, PartInfo> = {}
  for (const node of manifest.nodes) {
    // Only include nodes that have a mesh (visible parts)
    if (!node.mesh_id) continue

    const displayName = (node as AssemblyNode & { display_name?: string }).display_name
      || idToDisplayName(node.id)
    const group = inferGroup(node.id)
    const jointName = node.link_name ? jointByChild.get(node.link_name) : undefined

    metadata[node.id] = {
      name: node.id,
      displayName,
      group,
      jointName,
    }
  }
  return metadata
}
