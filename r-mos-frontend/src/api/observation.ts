/**
 * Observation API 模块
 */
import { apiClient } from './client'
import {
    Observation,
    ObservationCreateRequest,
    ObservationListResponse,
} from '@/types/observation'

export interface ListObservationsParams {
    page?: number
    size?: number
}

export async function listObservations(
    params: ListObservationsParams = {}
): Promise<ObservationListResponse> {
    const { page = 1, size = 20 } = params
    const response = await apiClient.get<ObservationListResponse>('/observations', {
        params: { page, size },
    })
    return response.data
}

export async function getObservation(observationId: string): Promise<Observation> {
    const response = await apiClient.get<Observation>(`/observations/${observationId}`)
    return response.data
}

export async function createObservation(data: ObservationCreateRequest): Promise<Observation> {
    const response = await apiClient.post<Observation>('/observations', data)
    return response.data
}
