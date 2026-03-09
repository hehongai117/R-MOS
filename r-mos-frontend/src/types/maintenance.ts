export interface MaintenanceDraftStep {
  step_id: string
  title: string
  description: string
  model_targets?: string[]
  required_tools?: string[]
  preconditions?: string[]
}

export interface MaintenanceCitation {
  chunk_id?: string
  title: string
  score?: number
  source?: string
}

export interface MaintenanceDraftPayload {
  title: string
  maintenance_goal: string
  steps: MaintenanceDraftStep[]
  tools?: string[]
  citations?: MaintenanceCitation[]
  model_targets?: string[]
  review_notes?: string[]
  manifest_tree?: {
    robot_key?: string
    root_nodes?: string[]
    nodes?: Array<{
      id: string
      display_name?: string
      parent_id?: string | null
      children?: string[]
      source_paths?: string[]
      runtime_asset_paths?: string[]
      file_kinds?: string[]
    }>
  }
  manifest_mapping?: Record<
    string,
    {
      source_paths?: string[]
      runtime_asset_paths?: string[]
      file_kinds?: string[]
    }
  >
}

export interface MaintenanceDraftResponse {
  draft_id: string
  project_id: string
  request_id: string
  review_status: string
  draft: MaintenanceDraftPayload
  verdict_steps: Array<Record<string, unknown>>
  viewer_manifest: {
    robotId: string
    label?: string
    parts: string[]
    assets?: Array<{
      asset_id: string
      asset_type: string
      display_name?: string
      node_id: string
      path: string
      source_paths?: string[]
    }>
    structures?: Array<{
      path: string
      structure_type: string
      root_nodes?: string[]
    }>
    needs_review_nodes?: string[]
  }
  manifest_tree: NonNullable<MaintenanceDraftPayload['manifest_tree']>
  manifest_mapping: NonNullable<MaintenanceDraftPayload['manifest_mapping']>
  citations: MaintenanceCitation[]
}

export interface MaintenanceDraftCreateRequest {
  project_id?: string
  robot_key?: string
  maintenance_goal: string
  focus_area?: string
  request_id?: string
}

export interface MaintenanceDraftUpdateRequest {
  title?: string
  maintenance_goal?: string
  steps?: MaintenanceDraftStep[]
  tools?: string[]
  review_notes?: string[]
}
