export type RobotId = "atom01";

const MODEL_BASE_URL = import.meta.env.VITE_MODEL_BASE_URL || "/models";

export const ROBOT_CATALOG: Record<RobotId, { label: string; basePath: string }> = {
  atom01: {
    label: "ATOM01",
    basePath: `${MODEL_BASE_URL}/robots/atom01`,
  },
};

export const getRobotModelBase = (robotId: RobotId) => {
  return ROBOT_CATALOG[robotId]?.basePath || `${MODEL_BASE_URL}/robots/${robotId}`;
};
