/**
 * manifestHelpers.ts — Utility functions for extracting data from RobotDataManifest.
 *
 * These helpers provide manifest-driven replacements for hardcoded constants
 * (e.g., JOINTS, CORE_LINKS, display_names). When a manifest is unavailable,
 * callers should fall back to their existing hardcoded data.
 */

import type { RobotDataManifest } from './assemblyManifest';

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
  return Object.keys(manifest.nodes);
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
