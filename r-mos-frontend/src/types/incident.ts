/**
 * Incident 类型定义
 */

export type IncidentType =
    | 'operational'
    | 'safety'
    | 'maintenance'
    | 'connectivity'
    | 'environmental'
    | 'unknown'

export type IncidentLevel = 'info' | 'warning' | 'critical'

export type IncidentStatus = 'open' | 'closed' | 'archived'

export interface IncidentCreateRequest {
    robot_id: string
    task_id?: number | null
    incident_type: IncidentType
    incident_level: IncidentLevel
    status?: IncidentStatus
    event_time_start: string
    event_time_end?: string | null
    human_summary?: string | null
    machine_tags?: string[] | null
    related_observation_ids?: string[] | null
    related_evidence_bundle_ids?: string[] | null
}

export interface Incident {
    incident_id: string
    robot_id: string
    task_id?: number | null
    incident_type: IncidentType
    incident_level: IncidentLevel
    status: IncidentStatus
    event_time_start: string
    event_time_end?: string | null
    ingest_time: string
    human_summary?: string | null
    machine_tags?: string[] | null
    related_observation_ids?: string[] | null
    related_evidence_bundle_ids?: string[] | null
}

export interface IncidentListItem {
    incident_id: string
    robot_id: string
    incident_type: IncidentType
    incident_level: IncidentLevel
    status: IncidentStatus
    event_time_start: string
    ingest_time: string
}

export interface IncidentListResponse {
    items: IncidentListItem[]
    total: number
    page: number
    size: number
    pages: number
}
