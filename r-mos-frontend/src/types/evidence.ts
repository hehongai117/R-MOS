/**
 * Evidence 类型定义
 */

export type EvidenceType = 'telemetry' | 'event' | 'sop_step' | 'media' | 'document' | 'log'

export type EvidenceBundleType =
    | 'telemetry_snapshot'
    | 'event_log'
    | 'sop_execution'
    | 'media'
    | 'mixed'

export type HashAlgo = 'sha256'

export interface EvidenceItem {
    evidence_id: string
    evidence_type: EvidenceType
    content_uri: string
    content_hash: string
    content_hash_algo: HashAlgo
    content_mime_type: string
    size_bytes: number
    observed_time: string
    ingest_time: string
    human_summary?: string | null
    machine_code?: string | null
    machine_tags?: string[] | null
}

export interface EvidenceBundleCreateRequest {
    bundle_type: EvidenceBundleType
    observed_time_start: string
    observed_time_end?: string | null
    items: EvidenceItem[]
    human_summary?: string | null
    machine_tags?: string[] | null
}

export interface EvidenceBundle extends EvidenceBundleCreateRequest {
    evidence_bundle_id: string
    bundle_hash: string
    bundle_hash_algo: HashAlgo
    ingest_time: string
    is_sealed: boolean
    sealed_at?: string | null
}

export interface EvidenceBundleListItem {
    evidence_bundle_id: string
    bundle_type: EvidenceBundleType
    observed_time_start: string
    ingest_time: string
    is_sealed: boolean
}

export interface EvidenceBundleListResponse {
    items: EvidenceBundleListItem[]
    total: number
    page: number
    size: number
    pages: number
}
