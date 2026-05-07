export type RobotId = string;  // was "atom01" literal, now dynamic

const MODEL_BASE_URL = import.meta.env.VITE_MODEL_BASE_URL || "/models";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/** Static fallback catalog for backward compatibility. */
export const STATIC_ROBOT_CATALOG: Record<string, { label: string; basePath: string }> = {
  atom01: {
    label: "ATOM01",
    basePath: `${MODEL_BASE_URL}/robots/atom01`,
  },
};

/**
 * Get the base URL for loading a robot's 3D model assets.
 *
 * For migrated robots (with numeric IDs), serves from the API.
 * For legacy robots (atom01), falls back to static paths.
 */
export const getRobotModelBase = (robotId: RobotId): string => {
  if (STATIC_ROBOT_CATALOG[robotId]) {
    return STATIC_ROBOT_CATALOG[robotId].basePath;
  }
  return `${API_BASE_URL}/api/v1/robots/${robotId}/assets/models`;
};

/**
 * Get the URL for a robot's manifest file.
 */
export const getRobotManifestUrl = (robotId: RobotId, manifestName: string): string => {
  if (STATIC_ROBOT_CATALOG[robotId]) {
    return `${STATIC_ROBOT_CATALOG[robotId].basePath}/${manifestName}`;
  }
  return `${API_BASE_URL}/api/v1/robots/${robotId}/assets/manifests/${manifestName}`;
};
