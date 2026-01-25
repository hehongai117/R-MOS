/**
 * Assessment 类型定义
 */

export type ProviderType = 'diagnosis' | 'phm' | 'insurance' | 'arbitration'

export type ProviderStatus = 'active' | 'suspended' | 'retired'

export type AssessmentStatus = 'active' | 'revoked' | 'disputed'

export type ReportFormat = 'pdf' | 'json' | 'html' | 'url' | 'archive' | 'other'

export type HashAlgo = 'sha256'

export type AuditAction = 'submitted' | 'revoked' | 'disputed' | 'reinstated'

export type ActorType = 'user' | 'system' | 'provider'

export type AssessmentReasonCode =
    | 'invalid_signature'
    | 'provider_withdrawn'
    | 'expired'
    | 'operator_error'
    | 'legal_hold'
    | 'other'

export type AssessmentReasonCodeWithNone = AssessmentReasonCode | 'none'

export interface AssessmentProviderCreateRequest {
    provider_name: string
    provider_type: ProviderType
    endpoint_uri?: string | null
    contact_name?: string | null
    contact_email?: string | null
}

export interface AssessmentProviderUpdateRequest {
    provider_name?: string | null
    endpoint_uri?: string | null
    contact_name?: string | null
    contact_email?: string | null
    status?: ProviderStatus
}

export interface AssessmentProvider {
    provider_id: string
    provider_name: string
    provider_type: ProviderType
    status: ProviderStatus
    endpoint_uri?: string | null
    contact_name?: string | null
    contact_email?: string | null
    created_at: string
    updated_at: string
}

export interface AssessmentProviderListResponse {
    items: AssessmentProvider[]
    total: number
    page: number
    size: number
    pages: number
}

export interface ExternalAssessmentCreateRequest {
    provider_id: string
    assessment_type: ProviderType
    provider_assessment_id?: string | null
    report_uri: string
    report_hash: string
    report_hash_algo: HashAlgo
    report_format: ReportFormat
    report_time: string
    evidence_bundle_ids?: string[] | null
    incident_ids?: string[] | null
    observation_ids?: string[] | null
}

export interface ExternalAssessment extends ExternalAssessmentCreateRequest {
    assessment_id: string
    provider_type: ProviderType
    ingest_time: string
    status: AssessmentStatus
    status_updated_at: string
}

export interface ExternalAssessmentListItem {
    assessment_id: string
    provider_id: string
    assessment_type: ProviderType
    status: AssessmentStatus
    report_time: string
    ingest_time: string
}

export interface ExternalAssessmentListResponse {
    items: ExternalAssessmentListItem[]
    total: number
    page: number
    size: number
    pages: number
}

export interface AssessmentStatusChangeRequest {
    reason_code: AssessmentReasonCode
    reason_note?: string | null
}

export interface AssessmentAuditEvent {
    audit_id: string
    assessment_id: string
    action: AuditAction
    actor_type: ActorType
    actor_id: string
    reason_code: AssessmentReasonCodeWithNone
    reason_note?: string | null
    event_time: string
    ingest_time: string
    trace_id: string
}

export interface AssessmentAuditTrail {
    assessment_id: string
    events: AssessmentAuditEvent[]
    total: number
}
