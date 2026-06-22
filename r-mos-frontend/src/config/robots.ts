import { API_BASE_URL } from '@/api/client'

export type RobotId = string;

/**
 * Get the base URL for loading a robot's 3D model assets from the API.
 */
export const getRobotModelBase = (robotId: RobotId): string => {
  return `${API_BASE_URL}/api/v1/robots/${robotId}/assets/models`;
};

/**
 * Get the URL for a robot's manifest file from the API.
 */
export const getRobotManifestUrl = (robotId: RobotId, manifestName: string): string => {
  return `${API_BASE_URL}/api/v1/robots/${robotId}/assets/manifests/${manifestName}`;
};
