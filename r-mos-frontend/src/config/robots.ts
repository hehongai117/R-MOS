import { API_BASE_URL } from '@/api/client'

export type RobotId = string;

/**
 * 精选默认机器人型号名。用户首次进入（无历史选择）时优先选中该型号，
 * 以保证默认打开的机器人拥有完整的 3D 资产与 manifest（演示/客户展示友好）。
 * 若列表中不存在该型号，则回退到列表首个机器人。设为 null 可关闭此偏好。
 */
export const DEFAULT_ROBOT_MODEL_NAME: string | null = 'ATOM-01';

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
