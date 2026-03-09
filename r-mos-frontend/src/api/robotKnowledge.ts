import client from './client'

import type {
  RobotProjectListResponse,
  RobotProjectManifest,
  RobotProjectUploadJob,
} from '@/types/robotKnowledge'

export async function listRobotProjects(): Promise<RobotProjectListResponse> {
  const response = await client.get<RobotProjectListResponse>('/agent/knowledge/projects')
  return response.data
}

export async function getRobotProjectManifest(projectId: string): Promise<RobotProjectManifest> {
  const response = await client.get<RobotProjectManifest>(`/agent/knowledge/projects/${projectId}/manifest`)
  return response.data
}

export async function uploadRobotProjectPackage(
  file: File,
  metadata: { brand?: string; model?: string; version?: string },
): Promise<RobotProjectUploadJob> {
  const formData = new FormData()
  formData.append('file', file)
  const query = new URLSearchParams()
  if (metadata.brand) {
    query.set('brand', metadata.brand)
  }
  if (metadata.model) {
    query.set('model', metadata.model)
  }
  if (metadata.version) {
    query.set('version', metadata.version)
  }
  const endpoint = query.size > 0 ? `/agent/knowledge/upload?${query.toString()}` : '/agent/knowledge/upload'
  const response = await client.post<RobotProjectUploadJob>(endpoint, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function getRobotProjectUploadJob(jobId: string): Promise<RobotProjectUploadJob> {
  const response = await client.get<RobotProjectUploadJob>(`/agent/knowledge/upload/${jobId}`)
  return response.data
}
