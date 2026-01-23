/**
 * Observation 类型定义
 */

export type ObservationType = 'telemetry' | 'event' | 'sop_step' | 'operator_note' | 'media'

export interface ObservationMetric {
    metric_name: string
    metric_value: number
    unit?: string | null
}

export interface ObservationCreateRequest {
    observation_type: ObservationType
    robot_id: string
    task_id?: number | null
    observed_time: string
    event_time?: string | null
    human_summary?: string | null
    machine_code?: string | null
    metrics?: ObservationMetric[] | null
    payload_uri?: string | null
    payload_hash?: string | null
}

export interface Observation extends ObservationCreateRequest {
    observation_id: string
    ingest_time: string
}

export interface ObservationListItem {
    observation_id: string
    observation_type: ObservationType
    robot_id: string
    observed_time: string
    ingest_time: string
}

export interface ObservationListResponse {
    items: ObservationListItem[]
    total: number
    page: number
    size: number
    pages: number
}
