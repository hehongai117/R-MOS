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
    TORSO_SCREW_INSTANCES,
    ALL_SCREW_INSTANCES,
    getScrewInstance,
    getAllScrewIds,
    getScrewsByParent,
} from './data/screwInstances';

export {
    FOOT_CONSTRAINTS,
    TORSO_CONSTRAINTS,
    ALL_CONSTRAINTS,
    getConstraintsByPart,
    getActiveConstraints,
    getConstraintById,
    getAllConstraints,
    canReleaseConstraint,
} from './data/constraintGraph';

export {
    CRITICAL_PARTS,
    isCriticalPart,
    getCriticalPartReason,
} from './data/criticalParts';

// 核心模块导出
export {
    useAdjudicationStore,
    useSystemState,
    useOperationMode,
    useCurrentTool,
    useScrewState,
    usePartState,
    getStateSnapshot,
    setScrewStateDirect,
    resetStateDirect,
} from './core/stateManager';

// 评分引擎
export {
    scoringEngine,
} from './core/scoringEngine';

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
    validateActionCompletion,
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
