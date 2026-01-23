/**
 * @description 裁决系统模块导出
 * @module adjudication
 */

// 类型导出
export * from './types/adjudication';

// 数据模块导出
export {
    PART_REGISTRY,
    PART_SCREWS_REGISTRY,
    getPartById,
    getPartScrews,
    getPartsByCategory,
    getAllPartIds,
} from './data/partRegistry';

export {
    FOOT_SCREW_INSTANCES,
    getScrewInstance,
    getAllScrewIds,
    getScrewsByParent,
} from './data/screwInstances';

export {
    FOOT_CONSTRAINTS,
    getConstraintsByPart,
    getActiveConstraints,
    getConstraintById,
    getAllConstraints,
    canReleaseConstraint,
} from './data/constraintGraph';

// 核心模块导出
export {
    useAdjudicationStore,
    useSystemState,
    useCurrentTool,
    useScrewState,
    usePartState,
    getStateSnapshot,
    setScrewStateDirect,
    resetStateDirect,
} from './core/stateManager';

// 几何判定模块导出
export {
    isScrewExtracted,
    getScrewProgress,
    getScrewGeometryCondition,
    getScrewGeometryConditionById,
    calculateDisplacementFromRotation,
    validateScrewRotation,
    checkPartScrewsExtracted,
    checkToolMatch,
} from './core/geometryJudge';

// 裁决引擎导出
export {
    canOperatePart,
    canRemoveScrew,
    canDetachPart,
    adjudicateAction,
    validateScrewExtraction,
    validatePartDetachment,
    commitScrewExtraction,
    commitPartDetachment,
    commitPartRemoval,
    getBlockingConstraints,
} from './core/decisionEngine';

// SOP 执行器导出
export {
    SOPExecutor,
    SOPExecutionState,
    createSOPExecutor,
    checkStepPreconditions,
    validateStepCompletion,
} from './executor/sopExecutor';
export type { SOPExecutionContext } from './executor/sopExecutor';
