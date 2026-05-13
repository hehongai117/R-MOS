import { apiClient } from './client'
import type {
  AnalysisTask,
  AnalysisTaskListResponse,
  FileUploadResponse,
  RobotModel,
  RobotModelCreateRequest,
  RobotModelListResponse,
  RobotModelUpdateRequest,
  SharedRobotListResponse,
} from '@/types/robotModel'

/** 列出当前教师名下的机器人 */
export async function listRobots(): Promise<RobotModelListResponse> {
  const response = await apiClient.get<RobotModelListResponse>('/robots')
  return response.data
}

/** 创建新机器人 */
export async function createRobot(data: RobotModelCreateRequest): Promise<RobotModel> {
  const response = await apiClient.post<RobotModel>('/robots', data)
  return response.data
}

/** 获取机器人详情 */
export async function getRobot(robotId: number): Promise<RobotModel> {
  const response = await apiClient.get<RobotModel>(`/robots/${robotId}`)
  return response.data
}

/** 更新机器人信息 */
export async function updateRobot(robotId: number, data: RobotModelUpdateRequest): Promise<RobotModel> {
  const response = await apiClient.put<RobotModel>(`/robots/${robotId}`, data)
  return response.data
}

/** 删除机器人 */
export async function deleteRobot(robotId: number): Promise<void> {
  await apiClient.delete(`/robots/${robotId}`)
}

/** 上传文件到机器人 */
export async function uploadRobotFiles(
  robotId: number,
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<FileUploadResponse> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  const response = await apiClient.post<FileUploadResponse>(
    `/robots/${robotId}/upload`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total))
        }
      },
    },
  )
  return response.data
}

/** 触发 AI 分析 */
export async function triggerAnalysis(robotId: number): Promise<AnalysisTask> {
  const response = await apiClient.post<AnalysisTask>(`/robots/${robotId}/analyze`)
  return response.data
}

/** 查看分析任务列表 */
export async function listAnalysisTasks(robotId: number): Promise<AnalysisTaskListResponse> {
  const response = await apiClient.get<AnalysisTaskListResponse>(`/robots/${robotId}/analysis-tasks`)
  return response.data
}

/** 发布/取消发布 */
export async function togglePublish(robotId: number): Promise<RobotModel> {
  const response = await apiClient.put<RobotModel>(`/robots/${robotId}/publish`)
  return response.data
}

/** 切换共享状态 */
export async function toggleVisibility(robotId: number): Promise<RobotModel> {
  const response = await apiClient.put<RobotModel>(`/robots/${robotId}/visibility`)
  return response.data
}

/** 学生查看可用机器人列表 */
export async function listStudentRobots(studentId: number): Promise<RobotModelListResponse> {
  const response = await apiClient.get<RobotModelListResponse>(`/students/${studentId}/robots`)
  return response.data
}

/** 浏览共享机器人库 */
export async function listSharedRobots(search?: string): Promise<SharedRobotListResponse> {
  const params = search ? { search } : {}
  const response = await apiClient.get<SharedRobotListResponse>('/robots/shared', { params })
  return response.data
}

/** 引用共享机器人 */
export async function bindSharedRobot(robotId: number): Promise<void> {
  await apiClient.post(`/robots/${robotId}/bind`)
}

/** 取消引用共享机器人 */
export async function unbindSharedRobot(robotId: number): Promise<void> {
  await apiClient.delete(`/robots/${robotId}/bind`)
}
