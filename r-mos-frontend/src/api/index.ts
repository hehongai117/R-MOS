/**
 * API 模块统一导出入口
 */

// API 客户端
export { apiClient } from './client'

// SOP API
export {
    listSOPs,
    getSOP,
    createSOP,
    checkDeleteImpact,
    deleteSOP,
} from './sop'
export type { ListSOPsParams } from './sop'

// Task API
export {
    createTask,
    getTask,
    startTask,
    executeStep,
    pauseTask,
    resumeTask,
    getTaskReport,
    listTasks,
} from './task'

// Adapter API
export {
    getAdapterInfo,
    getRobotStructure,
    injectFault,
    clearFault,
    getActiveFaults,
} from './adapter'
export type { FaultInjectionRequest } from './adapter'

// Fault Case API
export {
    listFaultCases,
    getFaultCase,
    createFaultCase,
    updateFaultCase,
    deleteFaultCase,
} from './fault'
