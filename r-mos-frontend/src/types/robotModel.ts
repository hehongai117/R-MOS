/** 机器人可见性 — 对齐后端 RobotVisibility enum */
export type RobotVisibility = 'private' | 'shared'

/** 机器人状态 — 对齐后端 RobotStatus enum */
export type RobotModelStatus = 'draft' | 'analyzing' | 'ready'

/** 资产类型 — 对齐后端 AssetType enum */
export type AssetType = 'model_glb' | 'manifest' | 'thumbnail' | 'upload_original'

/** 分析任务类型 */
export type AnalysisTaskType = 'pdf_extract' | 'cad_parse' | 'sop_generate' | 'full'

/** 分析任务状态 */
export type AnalysisTaskStatus = 'pending' | 'running' | 'completed' | 'failed'

/** 绑定类型 */
export type BindingType = 'owner' | 'shared_ref'

/** 机器人模型 — 对齐后端 RobotModelResponse */
export interface RobotModel {
  id: number
  brand: string
  model_name: string
  version: string
  owner_teacher_id: number | null
  visibility: RobotVisibility
  status: RobotModelStatus
  description: string | null
  thumbnail_path: string | null
  created_at: string
  updated_at: string
}

/** 机器人列表响应 */
export interface RobotModelListResponse {
  items: RobotModel[]
  total: number
}

/** 创建机器人请求体 */
export interface RobotModelCreateRequest {
  brand: string
  model_name: string
  version?: string
  description?: string
}

/** 更新机器人请求体 */
export interface RobotModelUpdateRequest {
  brand?: string
  model_name?: string
  version?: string
  description?: string
}

/** 机器人资产 */
export interface RobotAsset {
  id: number
  robot_model_id: number
  asset_type: AssetType
  file_path: string
  file_size: number | null
  metadata: Record<string, unknown> | null
  created_at: string
}

/** 文件上传响应 */
export interface FileUploadResponse {
  uploaded: RobotAsset[]
  failed: Array<{ filename: string; error: string }>
}

/** 分析任务 */
export interface AnalysisTask {
  id: number
  robot_model_id: number
  task_type: AnalysisTaskType
  status: AnalysisTaskStatus
  input_document_ids: number[] | null
  output_summary: Record<string, unknown> | null
  error_message: string | null
  completed_at: string | null
  created_at: string
}

/** 分析任务列表响应 */
export interface AnalysisTaskListResponse {
  items: AnalysisTask[]
  total: number
}

/** 类型守卫：判断机器人是否为 owner 创建 */
export function isOwnedRobot(robot: RobotModel, userId: number | undefined): boolean {
  return userId != null && robot.owner_teacher_id === userId
}

/** 类型守卫：判断机器人是否可发布 */
export function canPublish(robot: RobotModel): boolean {
  return robot.status === 'draft' || robot.status === 'ready'
}

/** 共享库机器人 — 含 owner 信息和引用状态 */
export interface SharedRobotModel {
  id: number
  brand: string
  model_name: string
  version: string
  owner_teacher_id: number | null
  owner_name: string | null
  visibility: RobotVisibility
  status: RobotModelStatus
  description: string | null
  thumbnail_path: string | null
  created_at: string
  updated_at: string
  is_bound: boolean
}

/** 共享库列表响应 */
export interface SharedRobotListResponse {
  items: SharedRobotModel[]
  total: number
}
