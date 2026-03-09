export interface RobotProjectUploadJob {
  job_id: string
  project_id: string
  status: string
  filename?: string | null
  content_type?: string | null
  size_bytes?: number | null
  brand?: string | null
  model?: string | null
  version?: string | null
}

export interface RobotProjectSummary {
  project_id: string
  robot_key: string
  brand: string
  model: string
  version?: string | null
  status: string
  ingest_summary?: {
    files_total?: number
    chunks_total?: number
    classification_kind?: string
    classification_strategy?: string
  } | null
}

export interface RobotProjectListResponse {
  projects: RobotProjectSummary[]
}

export interface RobotProjectManifest {
  project_id: string
  robot_key: string
  brand: string
  model: string
  version?: string | null
  status: string
  ingest_summary?: RobotProjectSummary['ingest_summary']
  tree: {
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
  mapping: Record<
    string,
    {
      source_paths?: string[]
      runtime_asset_paths?: string[]
      file_kinds?: string[]
    }
  >
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
}
