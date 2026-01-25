/**
 * Incident API 模块
 */
import { apiClient } from './client'
import { Incident, IncidentCreateRequest, IncidentListResponse } from '@/types/incident'

export interface ListIncidentsParams {
    page?: number
    size?: number
}

export async function listIncidents(params: ListIncidentsParams = {}): Promise<IncidentListResponse> {
    const { page = 1, size = 20 } = params
    const response = await apiClient.get<IncidentListResponse>('/incidents', {
        params: { page, size },
    })
    return response.data
}

export async function getIncident(incidentId: string): Promise<Incident> {
    const response = await apiClient.get<Incident>(`/incidents/${incidentId}`)
    return response.data
}

export async function createIncident(data: IncidentCreateRequest): Promise<Incident> {
    const response = await apiClient.post<Incident>('/incidents', data)
    return response.data
}
