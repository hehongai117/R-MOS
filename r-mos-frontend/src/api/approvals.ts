import { apiClient } from './client'

export interface ApprovalRecord {
  id: number
  trace_id?: string | null
  command_id?: number | null
  tool_call_id?: number | null
  status: string
  reason?: string | null
  created_by_user_id?: string | null
  decided_by_user_id?: string | null
  decided_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ApprovalListResponse {
  items: ApprovalRecord[]
  count: number
  limit: number
  offset: number
}

export async function listApprovals(params?: { status?: string; limit?: number; offset?: number }) {
  const response = await apiClient.get<ApprovalListResponse>('/ai/approvals', {
    params,
  })
  return response.data
}

export async function getApprovalDetail(id: number) {
  const response = await apiClient.get<ApprovalRecord>(`/ai/approvals/${id}`)
  return response.data
}

export async function grantApproval(id: number, reason?: string) {
  const response = await apiClient.post(`/ai/approvals/${id}/grant`, { reason })
  return response.data
}

export async function rejectApproval(id: number, reason?: string) {
  const response = await apiClient.post(`/ai/approvals/${id}/reject`, { reason })
  return response.data
}
