/**
 * Evidence API 模块
 */
import { apiClient } from './client'
import {
    EvidenceBundle,
    EvidenceBundleCreateRequest,
    EvidenceBundleListResponse,
} from '@/types/evidence'

export interface ListEvidenceBundlesParams {
    page?: number
    size?: number
}

export async function listEvidenceBundles(
    params: ListEvidenceBundlesParams = {}
): Promise<EvidenceBundleListResponse> {
    const { page = 1, size = 20 } = params
    const response = await apiClient.get<EvidenceBundleListResponse>('/evidence-bundles', {
        params: { page, size },
    })
    return response.data
}

export async function getEvidenceBundle(bundleId: string): Promise<EvidenceBundle> {
    const response = await apiClient.get<EvidenceBundle>(`/evidence-bundles/${bundleId}`)
    return response.data
}

export async function createEvidenceBundle(data: EvidenceBundleCreateRequest): Promise<EvidenceBundle> {
    const response = await apiClient.post<EvidenceBundle>('/evidence-bundles', data)
    return response.data
}
