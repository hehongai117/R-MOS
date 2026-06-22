import { apiClient } from './client'

export interface AdminUserSummary {
  id: number
  email: string
  full_name?: string | null
  is_active: boolean
  role: string
}

export interface AdminUsersResponse {
  items: AdminUserSummary[]
  total: number
}

export interface MonitorHealthResponse {
  overall_status?: string
  status?: string
  agent_available?: boolean
  websocket_clients?: number
  [key: string]: unknown
}

export interface MonitorMetricsResponse {
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  network_sent?: number
  network_recv?: number
  timestamp: string | number
}

export interface MonitorAlert {
  alert_id: string
  level: string
  component: string
  message: string
  created_at: string | number
  acknowledged: boolean
}

export interface MonitorAlertsResponse {
  alerts: MonitorAlert[]
}

export interface HealthResponse {
  status: string
  timestamp: string
  version: string
  checks: Record<string, { status: string; message?: string }>
}

export async function getAdminUsers(limit = 200) {
  const response = await apiClient.get<AdminUsersResponse>('/admin/users', { params: { limit } })
  return response.data
}

export async function getMonitorHealth() {
  const response = await apiClient.get<MonitorHealthResponse>('/agent/monitor/health')
  return response.data
}

export async function getMonitorMetrics() {
  const response = await apiClient.get<MonitorMetricsResponse>('/agent/monitor/metrics')
  return response.data
}

export async function getMonitorMetricsHistory(limit = 100) {
  const response = await apiClient.get<{ metrics: MonitorMetricsResponse[] }>(
    '/agent/monitor/metrics/history',
    { params: { limit } },
  )
  return response.data
}

export async function getMonitorAlerts(limit = 5) {
  const response = await apiClient.get<MonitorAlertsResponse>('/agent/monitor/alerts', {
    params: { limit },
  })
  return response.data
}

export async function getSystemHealth() {
  const response = await apiClient.get<HealthResponse>('/health')
  return response.data
}
