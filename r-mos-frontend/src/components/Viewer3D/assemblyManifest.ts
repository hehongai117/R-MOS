export type Vec3 = [number, number, number]
export type Quat = [number, number, number, number]

export interface AssemblyTransform {
  translation: Vec3
  rotation_quat: Quat
  scale: Vec3
}

export interface AssemblyNode {
  id: string
  parent_id: string | null
  children: string[]
  mesh_id: string | null
  display_name: string
  category: string
  link_name: string | null
  transform: AssemblyTransform
}

export interface AssemblyFastenerInstance {
  id: string
  type: string
  parent_id: string
  mesh_id: string
  transform: AssemblyTransform
  tool: string | null
  torque_nm: number | null
}

export interface AssemblyManifest {
  version: string
  robotId: string
  rootNodeId: string
  mesh_catalog: Record<string, string>
  nodes: AssemblyNode[]
  fastener_instances: AssemblyFastenerInstance[]
}

export interface ExplodeView {
  id: string
  focus_node_id: string
  camera: {
    projection: 'orthographic' | 'perspective'
    position: Vec3
    target: Vec3
  }
}

export interface ExplodeSequence {
  id: string
  step_index: number
  node_ids: string[]
  direction: Vec3
  distance: number
  anchor_node_id: string
}

export interface ExplodeManifest {
  version: string
  robotId: string
  views: ExplodeView[]
  sequences: ExplodeSequence[]
}

export interface AssemblyIndex {
  byId: Record<string, AssemblyNode>
  childrenByParent: Record<string, string[]>
}

// ---- Robot Data Manifest 扩展类型 ----

export interface ManifestPartEntry {
  id: string
  category: string              // 'frame' | 'cover' | 'screw' | 'motor' | 'pcb' | ...
  bom_code: string              // 'ATOM-01-BASE-001'
  display_name: string          // '髋部底座'
  parent_id: string | null
  mesh_id: string | null        // 引用 mesh_catalog
  local_position: Vec3
  local_rotation: Vec3           // euler angles
  group: string | null          // 'base' | 'torso' | 'left_arm' | ...
}

export interface ManifestScrewEntry {
  id: string
  bom_code: string
  parent_id: string             // 所属零件 ID
  position: Vec3
  axis: Vec3
  spec: {
    type: string                // 'M4×10'
    pitch: number
    thread_length: number
    required_tool: string       // 'hex_3'
    torque_nm: number
  }
}

export interface ManifestConstraintEntry {
  id: string
  type: 'fastened_by' | 'covered_by' | 'blocked_by'
  constrained_part: string
  constraining_part: string
  params: Record<string, unknown>
  release_condition: {
    type: string
    required_actions: string[]
  }
}

export interface ManifestCameraPreset {
  position: Vec3
  target: Vec3
  fov: number
}

export interface ManifestExplodeOffset {
  node_id: string
  direction: Vec3
  distance: number
}

export interface ManifestToolEntry {
  id: string
  name: string
  type: string                  // 'hex_key' | 'torque_wrench' | 'pliers'
  size: string
  description: string
}

export interface ManifestOverviewConfig {
  overview_nodes: string[]
  reference_set: string[]
  assembly_groups: Record<string, {
    display_name: string
    child_links: string[]
    explode_dir: Vec3
  }>
}

/** 完整的机器人数据清单 — 扩展 AssemblyManifest */
export interface RobotDataManifest extends AssemblyManifest {
  parts_registry?: ManifestPartEntry[]
  screw_instances?: ManifestScrewEntry[]
  constraints?: ManifestConstraintEntry[]
  camera_presets?: Record<string, ManifestCameraPreset>
  explode_offsets?: ManifestExplodeOffset[]
  tools?: ManifestToolEntry[]
  display_names?: Record<string, string>
  overview_config?: ManifestOverviewConfig
}

function expectRecord(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be an object`)
  }
  return value as Record<string, unknown>
}

function expectString(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${label} must be a non-empty string`)
  }
  return value
}

function expectNullableString(value: unknown, label: string): string | null {
  if (value == null) {
    return null
  }
  return expectString(value, label)
}

function expectStringArray(value: unknown, label: string): string[] {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string' || entry.trim() === '')) {
    throw new Error(`${label} must be an array of non-empty strings`)
  }
  return value.slice()
}

function expectNumber(value: unknown, label: string): number {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    throw new Error(`${label} must be a number`)
  }
  return value
}

function expectTuple(value: unknown, label: string, length: number): number[] {
  if (!Array.isArray(value) || value.length !== length || value.some((entry) => typeof entry !== 'number' || Number.isNaN(entry))) {
    throw new Error(`${label} must be a numeric tuple of length ${length}`)
  }
  return value.slice()
}

function parseTransform(rawValue: unknown, label: string): AssemblyTransform {
  if (rawValue == null) {
    throw new Error(`${label} is missing transform`)
  }
  const raw = expectRecord(rawValue, `${label}.transform`)
  return {
    translation: expectTuple(raw.translation, `${label}.transform.translation`, 3) as Vec3,
    rotation_quat: expectTuple(raw.rotation_quat, `${label}.transform.rotation_quat`, 4) as Quat,
    scale: expectTuple(raw.scale, `${label}.transform.scale`, 3) as Vec3,
  }
}

function parseNode(rawValue: unknown): AssemblyNode {
  const raw = expectRecord(rawValue, 'assembly node')
  const id = expectString(raw.id, 'assembly node id')
  return {
    id,
    parent_id: raw.parent_id === null ? null : expectNullableString(raw.parent_id, `assembly node ${id} parent_id`),
    children: Array.isArray(raw.children) ? expectStringArray(raw.children, `assembly node ${id} children`) : [],
    mesh_id: raw.mesh_id === null ? null : expectNullableString(raw.mesh_id, `assembly node ${id} mesh_id`),
    display_name: expectString(raw.display_name, `assembly node ${id} display_name`),
    category: expectString(raw.category, `assembly node ${id} category`),
    link_name: raw.link_name == null ? null : expectString(raw.link_name, `assembly node ${id} link_name`),
    transform: parseTransform(raw.transform, `assembly node ${id}`),
  }
}

function parseFastenerInstance(rawValue: unknown): AssemblyFastenerInstance {
  const raw = expectRecord(rawValue, 'assembly fastener')
  const id = expectString(raw.id, 'assembly fastener id')
  return {
    id,
    type: expectString(raw.type, `assembly fastener ${id} type`),
    parent_id: expectString(raw.parent_id, `assembly fastener ${id} parent_id`),
    mesh_id: expectString(raw.mesh_id, `assembly fastener ${id} mesh_id`),
    transform: parseTransform(raw.transform, `assembly fastener ${id}`),
    tool: raw.tool == null ? null : expectString(raw.tool, `assembly fastener ${id} tool`),
    torque_nm: raw.torque_nm == null ? null : expectNumber(raw.torque_nm, `assembly fastener ${id} torque_nm`),
  }
}

export function parseAssemblyManifest(rawValue: unknown): AssemblyManifest {
  const raw = expectRecord(rawValue, 'assembly manifest')
  const meshCatalog = expectRecord(raw.mesh_catalog, 'assembly manifest mesh_catalog')

  return {
    version: expectString(raw.version, 'assembly manifest version'),
    robotId: expectString(raw.robotId, 'assembly manifest robotId'),
    rootNodeId: expectString(raw.rootNodeId, 'assembly manifest rootNodeId'),
    mesh_catalog: Object.fromEntries(
      Object.entries(meshCatalog).map(([meshId, meshPath]) => [meshId, expectString(meshPath, `mesh_catalog.${meshId}`)]),
    ),
    nodes: Array.isArray(raw.nodes) ? raw.nodes.map((node) => parseNode(node)) : (() => {
      throw new Error('assembly manifest nodes must be an array')
    })(),
    fastener_instances: Array.isArray(raw.fastener_instances)
      ? raw.fastener_instances.map((instance) => parseFastenerInstance(instance))
      : (() => {
        throw new Error('assembly manifest fastener_instances must be an array')
      })(),
  }
}

export function parseRobotDataManifest(raw: unknown): RobotDataManifest {
  const base = parseAssemblyManifest(raw)
  const obj = raw as Record<string, unknown>
  return {
    ...base,
    parts_registry: (obj.parts_registry as ManifestPartEntry[]) ?? [],
    screw_instances: (obj.screw_instances as ManifestScrewEntry[]) ?? [],
    constraints: (obj.constraints as ManifestConstraintEntry[]) ?? [],
    camera_presets: (obj.camera_presets as Record<string, ManifestCameraPreset>) ?? {},
    explode_offsets: (obj.explode_offsets as ManifestExplodeOffset[]) ?? [],
    tools: (obj.tools as ManifestToolEntry[]) ?? [],
    display_names: (obj.display_names as Record<string, string>) ?? {},
    overview_config: (obj.overview_config as ManifestOverviewConfig) ?? undefined,
  }
}

function parseExplodeView(rawValue: unknown): ExplodeView {
  const raw = expectRecord(rawValue, 'explode view')
  const camera = expectRecord(raw.camera, `explode view ${raw.id ?? '<unknown>'} camera`)
  const projection = expectString(camera.projection, `explode view ${raw.id ?? '<unknown>'} camera.projection`)
  if (projection !== 'orthographic' && projection !== 'perspective') {
    throw new Error(`explode view ${raw.id ?? '<unknown>'} camera.projection must be orthographic or perspective`)
  }
  return {
    id: expectString(raw.id, 'explode view id'),
    focus_node_id: expectString(raw.focus_node_id, `explode view ${raw.id ?? '<unknown>'} focus_node_id`),
    camera: {
      projection,
      position: expectTuple(camera.position, `explode view ${raw.id ?? '<unknown>'} camera.position`, 3) as Vec3,
      target: expectTuple(camera.target, `explode view ${raw.id ?? '<unknown>'} camera.target`, 3) as Vec3,
    },
  }
}

function parseExplodeSequence(rawValue: unknown): ExplodeSequence {
  const raw = expectRecord(rawValue, 'explode sequence')
  const id = expectString(raw.id, 'explode sequence id')
  return {
    id,
    step_index: expectNumber(raw.step_index, `explode sequence ${id} step_index`),
    node_ids: expectStringArray(raw.node_ids, `explode sequence ${id} node_ids`),
    direction: expectTuple(raw.direction, `explode sequence ${id} direction`, 3) as Vec3,
    distance: expectNumber(raw.distance, `explode sequence ${id} distance`),
    anchor_node_id: expectString(raw.anchor_node_id, `explode sequence ${id} anchor_node_id`),
  }
}

export function parseExplodeManifest(rawValue: unknown): ExplodeManifest {
  const raw = expectRecord(rawValue, 'explode manifest')
  return {
    version: expectString(raw.version, 'explode manifest version'),
    robotId: expectString(raw.robotId, 'explode manifest robotId'),
    views: Array.isArray(raw.views) ? raw.views.map((view) => parseExplodeView(view)) : (() => {
      throw new Error('explode manifest views must be an array')
    })(),
    sequences: Array.isArray(raw.sequences) ? raw.sequences.map((sequence) => parseExplodeSequence(sequence)) : (() => {
      throw new Error('explode manifest sequences must be an array')
    })(),
  }
}

export function resolveExplodeView(
  manifest: ExplodeManifest,
  viewId: string | null | undefined,
): ExplodeView | null {
  if (!viewId) {
    return manifest.views[0] ?? null
  }

  return manifest.views.find((view) => view.id === viewId) ?? null
}

export function buildAssemblyIndex(manifest: AssemblyManifest): AssemblyIndex {
  const byId = Object.fromEntries(manifest.nodes.map((node) => [node.id, node]))
  const childrenByParent = manifest.nodes.reduce<Record<string, string[]>>((acc, node) => {
    acc[node.id] = node.children.slice()
    return acc
  }, {})

  manifest.nodes.forEach((node) => {
    if (node.parent_id) {
      const parentChildren = childrenByParent[node.parent_id] ?? []
      if (!parentChildren.includes(node.id)) {
        childrenByParent[node.parent_id] = [...parentChildren, node.id]
      }
    }
  })

  return { byId, childrenByParent }
}

export function collectAssemblyDescendants(index: AssemblyIndex, nodeId: string): string[] {
  const queue = [...(index.childrenByParent[nodeId] ?? [])]
  const descendants: string[] = []
  while (queue.length > 0) {
    const current = queue.shift()
    if (!current) continue
    descendants.push(current)
    queue.push(...(index.childrenByParent[current] ?? []))
  }
  return descendants
}
