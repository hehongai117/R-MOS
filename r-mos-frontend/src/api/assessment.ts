/**
 * Assessment API 模块
 */
import { apiClient } from './client'
import {
    AssessmentProvider,
    AssessmentProviderCreateRequest,
    AssessmentProviderListResponse,
    AssessmentProviderUpdateRequest,
    ExternalAssessment,
    ExternalAssessmentCreateRequest,
    ExternalAssessmentListResponse,
    AssessmentAuditTrail,
    AssessmentStatusChangeRequest,
} from '@/types/assessment'

export interface ListProvidersParams {
    page?: number
    size?: number
}

export async function listAssessmentProviders(
    params: ListProvidersParams = {}
): Promise<AssessmentProviderListResponse> {
    const { page = 1, size = 20 } = params
    const response = await apiClient.get<AssessmentProviderListResponse>('/assessment-providers', {
        params: { page, size },
    })
    return response.data
}

export async function createAssessmentProvider(
    data: AssessmentProviderCreateRequest
): Promise<AssessmentProvider> {
    const response = await apiClient.post<AssessmentProvider>('/assessment-providers', data)
    return response.data
}

export async function updateAssessmentProvider(
    providerId: string,
    data: AssessmentProviderUpdateRequest
): Promise<AssessmentProvider> {
    const response = await apiClient.patch<AssessmentProvider>(`/assessment-providers/${providerId}`, data)
    return response.data
}

export async function getAssessmentProvider(providerId: string): Promise<AssessmentProvider> {
    const response = await apiClient.get<AssessmentProvider>(`/assessment-providers/${providerId}`)
    return response.data
}

export interface ListAssessmentsParams {
    page?: number
    size?: number
}

export async function listAssessments(
    params: ListAssessmentsParams = {}
): Promise<ExternalAssessmentListResponse> {
    const { page = 1, size = 20 } = params
    const response = await apiClient.get<ExternalAssessmentListResponse>('/assessments', {
        params: { page, size },
    })
    return response.data
}

export async function createAssessment(
    data: ExternalAssessmentCreateRequest
): Promise<ExternalAssessment> {
    const response = await apiClient.post<ExternalAssessment>('/assessments', data)
    return response.data
}

export async function getAssessment(assessmentId: string): Promise<ExternalAssessment> {
    const response = await apiClient.get<ExternalAssessment>(`/assessments/${assessmentId}`)
    return response.data
}

export async function getAssessmentAudit(assessmentId: string): Promise<AssessmentAuditTrail> {
    const response = await apiClient.get<AssessmentAuditTrail>(`/assessments/${assessmentId}/audit`)
    return response.data
}

export async function revokeAssessment(
    assessmentId: string,
    data: AssessmentStatusChangeRequest
): Promise<ExternalAssessment> {
    const response = await apiClient.post<ExternalAssessment>(`/assessments/${assessmentId}/revoke`, data)
    return response.data
}

export async function disputeAssessment(
    assessmentId: string,
    data: AssessmentStatusChangeRequest
): Promise<ExternalAssessment> {
    const response = await apiClient.post<ExternalAssessment>(`/assessments/${assessmentId}/dispute`, data)
    return response.data
}

export async function reinstateAssessment(
    assessmentId: string,
    data: AssessmentStatusChangeRequest
): Promise<ExternalAssessment> {
    const response = await apiClient.post<ExternalAssessment>(`/assessments/${assessmentId}/reinstate`, data)
    return response.data
}
