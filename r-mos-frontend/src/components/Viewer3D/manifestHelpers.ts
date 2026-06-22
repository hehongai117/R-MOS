/**
 * manifestHelpers.ts — Utility functions for extracting data from RobotDataManifest.
 *
 * These helpers provide manifest-driven replacements for hardcoded constants
 * (e.g., JOINTS, CORE_LINKS, display_names). When a manifest is unavailable,
 * callers should fall back to their existing hardcoded data.
 */

import type { RobotDataManifest } from './assemblyManifest';

// Re-export DetailPart type shape for helpers (avoid circular import by using inline type)
type DetailPartLike = { displayName: string; path: string; category: string; actionTarget?: string };

/**
 * Build a joint-axis map from manifest joints.
 * Returns a Record keyed by joint name whose value is the rotation axis vector.
 * Joints without an axis field are omitted.
 */
export function buildJointAxisMap(
  manifest: RobotDataManifest | null | undefined
): Record<string, [number, number, number]> {
  if (!manifest?.joints) return {};
  const map: Record<string, [number, number, number]> = {};
  for (const joint of manifest.joints) {
    if (joint.axis) {
      map[joint.name] = joint.axis;
    }
  }
  return map;
}

/**
 * Extract the list of core link IDs from manifest nodes.
 * Returns an empty array when the manifest is not available.
 */
export function buildCoreLinkList(
  manifest: RobotDataManifest | null | undefined
): string[] {
  if (!manifest?.nodes) return [];
  return manifest.nodes.map((node) => node.id);
}

/**
 * Return the display_names mapping from the manifest.
 * Returns an empty object when the manifest is not available.
 */
export function buildDisplayNameMap(
  manifest: RobotDataManifest | null | undefined
): Record<string, string> {
  return manifest?.display_names ?? {};
}

/**
 * Build a detail parts map from the manifest's detail_parts field.
 * Returns null when the manifest has no detail_parts (caller should use its own fallback).
 * The returned map has the same shape as the hardcoded EXTRA_LINK_PARTS / DetailPart[].
 */
export function buildDetailPartsMap(
  manifest: RobotDataManifest | null | undefined
): Record<string, DetailPartLike[]> | null {
  if (!manifest?.detail_parts) return null;
  return manifest.detail_parts as Record<string, DetailPartLike[]>;
}

/**
 * Build a per-node explode offset map from the manifest's explode_offsets array.
 * Returns null when the manifest has no explode_offsets (caller should use its own fallback).
 */
export function buildExplodeOffsetMap(
  manifest: RobotDataManifest | null | undefined
): Record<string, [number, number, number]> | null {
  const offsets = manifest?.explode_offsets;
  if (!offsets?.length) return null;
  const map: Record<string, [number, number, number]> = {};
  for (const entry of offsets) {
    map[entry.node_id] = entry.offset;
  }
  return map;
}

// ---- buildPartMetadata ----

type PartGroup = 'base' | 'torso' | 'left_arm' | 'right_arm' | 'left_leg' | 'right_leg';
type PartMeta = { name: string; displayName: string; group: PartGroup; jointName?: string };

/** Infer a part group from the link ID when assembly_groups data is unavailable. */
function inferGroupFromLinkId(linkId: string): PartGroup {
  if (linkId.startsWith('left_arm') || linkId.startsWith('left_elbow')) return 'left_arm';
  if (linkId.startsWith('right_arm') || linkId.startsWith('right_elbow')) return 'right_arm';
  if (
    linkId.startsWith('left_thigh') ||
    linkId.startsWith('left_knee') ||
    linkId.startsWith('left_ankle')
  ) return 'left_leg';
  if (
    linkId.startsWith('right_thigh') ||
    linkId.startsWith('right_knee') ||
    linkId.startsWith('right_ankle')
  ) return 'right_leg';
  if (linkId.includes('torso')) return 'torso';
  return 'base';
}

/**
 * Build a PartMeta map from the manifest's display_names, joints, and assembly_groups.
 * Returns null when the manifest has no display_names (caller should use its own fallback).
 */
export function buildPartMetadata(
  manifest: RobotDataManifest | null | undefined
): Record<string, PartMeta> | null {
  if (!manifest?.display_names) return null;

  const displayNames = manifest.display_names;
  const groups = manifest.overview_config?.assembly_groups;
  const joints = manifest.joints;

  // Build link → group reverse lookup from assembly_groups
  const linkToGroup: Record<string, PartGroup> = {};
  if (groups) {
    for (const [groupKey, group] of Object.entries(groups)) {
      // Normalise group key: strip trailing _link, _pitch, _yaw, _roll suffixes
      const normKey = groupKey
        .replace(/_link$/, '')
        .replace(/_(pitch|yaw|roll)$/, '');
      // Validate it is one of the known groups, otherwise infer per-link
      const knownGroups: PartGroup[] = ['base', 'torso', 'left_arm', 'right_arm', 'left_leg', 'right_leg'];
      const resolvedGroup = knownGroups.includes(normKey as PartGroup)
        ? (normKey as PartGroup)
        : null;
      for (const childLink of group.child_links) {
        linkToGroup[childLink] = resolvedGroup ?? inferGroupFromLinkId(childLink);
      }
    }
  }

  // Build link → joint name for non-fixed joints
  const linkToJoint: Record<string, string> = {};
  if (joints) {
    for (const joint of joints) {
      if (joint.type !== 'fixed') {
        linkToJoint[joint.child_link] = joint.name;
      }
    }
  }

  // Build the result record
  const result: Record<string, PartMeta> = {};
  for (const [linkId, displayName] of Object.entries(displayNames)) {
    result[linkId] = {
      name: linkId,
      displayName,
      group: linkToGroup[linkId] ?? inferGroupFromLinkId(linkId),
      jointName: linkToJoint[linkId],
    };
  }

  return result;
}

// Inline types to avoid circular import with disassemblyConfig.ts
type ScrewAnimConfigLike = {
  id: string
  glbPath: string
  position: [number, number, number]
  axis: [number, number, number]
  extractDistance: number
  rotations: number
  parentLink: string
  label: string
}

type PartAnimConfigLike = {
  linkName: string
  detachOffset: [number, number, number]
  label: string
}

/**
 * Build disassembly config (screw sequence + part sequence) from the manifest.
 * Returns null when the manifest has no disassembly_config (caller should fall back
 * to the hardcoded SCREW_SEQUENCE / PART_SEQUENCE constants).
 *
 * The returned types are structurally compatible with ScrewAnimConfig and PartAnimConfig
 * from disassemblyConfig.ts (no circular import needed).
 */
export function buildDisassemblyConfig(
  manifest: RobotDataManifest | null | undefined,
): { screwSequence: ScrewAnimConfigLike[]; partSequence: PartAnimConfigLike[] } | null {
  const dc = manifest?.disassembly_config;
  if (!dc) return null;

  const screwSequence: ScrewAnimConfigLike[] = (dc.screw_sequence ?? []).map((s) => ({
    id: s.id,
    glbPath: s.glbPath,
    position: s.position,
    axis: s.axis,
    extractDistance: s.extractDistance,
    rotations: s.rotations,
    parentLink: s.parentLink,
    label: s.label,
  }));

  const partSequence: PartAnimConfigLike[] = (dc.part_sequence ?? []).map((p) => ({
    linkName: p.id,
    detachOffset: p.direction,
    label: p.label,
  }));

  return { screwSequence, partSequence };
}
