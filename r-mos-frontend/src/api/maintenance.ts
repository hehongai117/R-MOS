import client from './client'

import type {
  MaintenanceDraftCreateRequest,
  MaintenanceDraftResponse,
  MaintenanceDraftUpdateRequest,
} from '@/types/maintenance'

export async function createMaintenanceDraft(
  payload: MaintenanceDraftCreateRequest,
): Promise<MaintenanceDraftResponse> {
  const response = await client.post<MaintenanceDraftResponse>('/maintenance/drafts', payload)
  return response.data
}

export async function getMaintenanceDraft(draftId: string): Promise<MaintenanceDraftResponse> {
  const response = await client.get<MaintenanceDraftResponse>(`/maintenance/drafts/${draftId}`)
  return response.data
}

export async function updateMaintenanceDraft(
  draftId: string,
  payload: MaintenanceDraftUpdateRequest,
): Promise<MaintenanceDraftResponse> {
  const response = await client.patch<MaintenanceDraftResponse>(`/maintenance/drafts/${draftId}`, payload)
  return response.data
}

export async function submitMaintenanceDraftReview(draftId: string): Promise<MaintenanceDraftResponse> {
  const response = await client.post<MaintenanceDraftResponse>(`/maintenance/drafts/${draftId}/submit-review`)
  return response.data
}

export async function approveMaintenanceDraft(draftId: string): Promise<MaintenanceDraftResponse> {
  const response = await client.post<MaintenanceDraftResponse>(`/maintenance/drafts/${draftId}/approve`)
  return response.data
}

export async function rejectMaintenanceDraft(
  draftId: string,
  reason: string,
): Promise<MaintenanceDraftResponse> {
  const response = await client.post<MaintenanceDraftResponse>(`/maintenance/drafts/${draftId}/reject`, {
    reason,
  })
  return response.data
}

export async function getExecutableMaintenanceDraft(projectId: string): Promise<MaintenanceDraftResponse> {
  const response = await client.get<MaintenanceDraftResponse>(`/maintenance/projects/${projectId}/executable-draft`)
  return response.data
}
