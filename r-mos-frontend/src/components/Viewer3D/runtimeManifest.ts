import { ActionType, ErrorCategory, type SOPFailureReason, type SOPScriptAdjudication } from '@/adjudication'
import type { MaintenanceDraftResponse } from '@/types/maintenance'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const API_ROOT = `${API_BASE_URL}/api/v1`

const DEFAULT_FAILURE_REASONS: SOPFailureReason[] = [
  {
    code: 'RUNTIME_STEP_BLOCKED',
    category: ErrorCategory.INCOMPLETE_ACTION,
    description: '运行时草案步骤需要人工确认后才能继续。',
    severity: 'major',
    teachingResponse: {
      showHint: true,
      hintContent: '请结合当前步骤描述与引用依据执行检查。',
      allowRetry: true,
    },
    examResponse: {
      deductPoints: 2,
      allowContinue: false,
      recordToReport: true,
    },
  },
]

export type RuntimeAssetFormat = 'gltf' | 'stl' | 'obj' | 'dae' | 'wrl' | 'unsupported'

export interface RuntimeAssetDescriptor {
  assetId: string
  assetType: RuntimeAssetFormat
  displayName: string
  nodeId: string
  path: string
  sourcePaths: string[]
}

export interface RuntimeManifestTreeNode {
  id: string
  display_name?: string
  parent_id?: string | null
  children?: string[]
  source_paths?: string[]
  runtime_asset_paths?: string[]
  file_kinds?: string[]
}

export interface ViewerTreeNodeAdapter {
  id: string
  displayName: string
  parentId: string | null
  children: string[]
  runtimeAssetPaths: string[]
  sourcePaths: string[]
  fileKinds: string[]
}

export interface ViewerTreeAdapter {
  rootNodeIds: string[]
  nodes: Record<string, ViewerTreeNodeAdapter>
}

export interface RuntimeManifestAdapter {
  projectId: string
  robotId: string
  label: string
  parts: string[]
  assets: RuntimeAssetDescriptor[]
  reviewWarnings: string[]
  mapping: Record<string, { source_paths?: string[]; file_kinds?: string[]; runtime_asset_paths?: string[] }>
  treeNodes: Record<string, RuntimeManifestTreeNode>
  tree: ViewerTreeAdapter
  assetUrls: string[]
}

export function buildRobotProjectAssetUrl(projectId: string, assetPath: string) {
  const encodedPath = assetPath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/')
  return `${API_ROOT}/agent/knowledge/projects/${projectId}/assets/${encodedPath}`
}

export function detectRuntimeAssetFormat(assetPath: string | null | undefined): RuntimeAssetFormat {
  if (!assetPath) {
    return 'unsupported'
  }
  const normalized = assetPath.toLowerCase()
  if (normalized.endsWith('.glb') || normalized.endsWith('.gltf')) {
    return 'gltf'
  }
  if (normalized.endsWith('.stl')) {
    return 'stl'
  }
  if (normalized.endsWith('.obj')) {
    return 'obj'
  }
  if (normalized.endsWith('.dae')) {
    return 'dae'
  }
  if (normalized.endsWith('.wrl')) {
    return 'wrl'
  }
  return 'unsupported'
}

function normalizeRuntimeAsset(asset: Record<string, unknown>): RuntimeAssetDescriptor | null {
  const path = typeof asset.path === 'string' ? asset.path : null
  const nodeId = typeof asset.node_id === 'string' ? asset.node_id : null
  if (!path || !nodeId) {
    return null
  }
  return {
    assetId: typeof asset.asset_id === 'string' ? asset.asset_id : `${nodeId}::${path}`,
    assetType: detectRuntimeAssetFormat(path),
    displayName: typeof asset.display_name === 'string' ? asset.display_name : nodeId,
    nodeId,
    path,
    sourcePaths: Array.isArray(asset.source_paths) ? asset.source_paths.filter((value): value is string => typeof value === 'string') : [],
  }
}

function sortRuntimePaths(paths: Iterable<string>): string[] {
  const priority: Record<RuntimeAssetFormat, number> = {
    gltf: 0,
    stl: 1,
    obj: 2,
    dae: 3,
    wrl: 4,
    unsupported: 99,
  }
  return Array.from(new Set(paths))
    .filter((path) => detectRuntimeAssetFormat(path) !== 'unsupported')
    .sort((left, right) => {
      const leftFormat = detectRuntimeAssetFormat(left)
      const rightFormat = detectRuntimeAssetFormat(right)
      return priority[leftFormat] - priority[rightFormat] || left.localeCompare(right)
    })
}

function normalizeViewerTreeNode(node: RuntimeManifestTreeNode): ViewerTreeNodeAdapter {
  return {
    id: node.id,
    displayName: node.display_name || node.id,
    parentId: node.parent_id ?? null,
    children: node.children ?? [],
    runtimeAssetPaths: sortRuntimePaths(node.runtime_asset_paths ?? []),
    sourcePaths: Array.isArray(node.source_paths) ? node.source_paths.filter((value): value is string => typeof value === 'string') : [],
    fileKinds: Array.isArray(node.file_kinds) ? node.file_kinds.filter((value): value is string => typeof value === 'string') : [],
  }
}

function createViewerTreeAdapter(
  rootNodeIds: string[] | undefined,
  treeNodes: Record<string, RuntimeManifestTreeNode>,
): ViewerTreeAdapter {
  return {
    rootNodeIds: rootNodeIds && rootNodeIds.length > 0 ? rootNodeIds : Object.values(treeNodes)
      .filter((node) => (node.parent_id ?? null) === null)
      .map((node) => node.id),
    nodes: Object.fromEntries(
      Object.values(treeNodes).map((node) => [node.id, normalizeViewerTreeNode(node)]),
    ),
  }
}

export function createRuntimeManifestAdapter(draft: MaintenanceDraftResponse): RuntimeManifestAdapter {
  const treeNodes = Object.fromEntries(
    (draft.manifest_tree.nodes ?? []).map((node) => [node.id, node]),
  )

  const assets = ((draft.viewer_manifest.assets ?? []) as Array<Record<string, unknown>>)
    .map(normalizeRuntimeAsset)
    .filter((asset): asset is RuntimeAssetDescriptor => asset !== null)

  const parts = draft.viewer_manifest.parts && draft.viewer_manifest.parts.length > 0
    ? sortRuntimePaths(draft.viewer_manifest.parts)
    : sortRuntimePaths(assets.map((asset) => asset.path))

  return {
    projectId: draft.project_id,
    robotId: draft.viewer_manifest.robotId,
    label: draft.viewer_manifest.label || draft.draft.title || draft.viewer_manifest.robotId,
    parts,
    assets,
    reviewWarnings: draft.viewer_manifest.needs_review_nodes?.map((node) => `part mapping requires review: ${node}`) ??
      draft.draft.review_notes ??
      [],
    mapping: draft.manifest_mapping ?? {},
    treeNodes,
    tree: createViewerTreeAdapter(draft.manifest_tree.root_nodes, treeNodes),
    assetUrls: parts.map((part) => buildRobotProjectAssetUrl(draft.project_id, part)),
  }
}

function collectDescendantAssetPaths(
  adapter: RuntimeManifestAdapter,
  nodeId: string,
  visited: Set<string>,
  resolved: Set<string>,
) {
  if (visited.has(nodeId)) {
    return
  }
  visited.add(nodeId)
  const node = adapter.treeNodes[nodeId]
  if (!node) {
    return
  }
  for (const runtimePath of node.runtime_asset_paths ?? []) {
    if (detectRuntimeAssetFormat(runtimePath) !== 'unsupported') {
      resolved.add(runtimePath)
    }
  }
  for (const childId of node.children ?? []) {
    collectDescendantAssetPaths(adapter, childId, visited, resolved)
  }
}

export function resolveRuntimeAssetPaths(
  adapter: RuntimeManifestAdapter,
  targetIds: string[],
): string[] {
  const resolved = new Set<string>()
  for (const targetId of targetIds) {
    const runtimePaths = adapter.mapping[targetId]?.runtime_asset_paths ?? []
    for (const runtimePath of runtimePaths) {
      if (detectRuntimeAssetFormat(runtimePath) !== 'unsupported') {
        resolved.add(runtimePath)
      }
    }
    if (resolved.size > 0) {
      continue
    }
    collectDescendantAssetPaths(adapter, targetId, new Set<string>(), resolved)
    if (resolved.size > 0) {
      continue
    }
    const sourcePaths = adapter.mapping[targetId]?.source_paths ?? []
    for (const sourcePath of sourcePaths) {
      if (detectRuntimeAssetFormat(sourcePath) !== 'unsupported') {
        resolved.add(sourcePath)
      }
    }
  }
  const sortedResolved = sortRuntimePaths(resolved)
  if (sortedResolved.length > 0) {
    return sortedResolved
  }
  return adapter.parts.slice(0, 1)
}

export function buildRuntimeSopScript(draft: MaintenanceDraftResponse): SOPScriptAdjudication {
  const steps = draft.draft.steps.map((step, index) => ({
    stepId: step.step_id,
    stepIndex: index + 1,
    title: step.title,
    description: step.description,
    action: step.required_tools?.length ? ActionType.SELECT_TOOL : ActionType.FOCUS_CAMERA,
    targetParts: step.model_targets ?? [],
    requiredTool: step.required_tools?.[0] ?? null,
    preconditions: [],
    validations: [],
    failureReasons: DEFAULT_FAILURE_REASONS,
    onSuccess: {
      nextStepId: draft.draft.steps[index + 1]?.step_id ?? step.step_id,
      stateTransition: null,
    },
    onFailure: {
      action: 'block' as const,
      message: '请先完成当前运行时草案步骤的确认。',
    },
  }))

  return {
    sopId: `runtime-${draft.draft_id}`,
    title: draft.draft.title,
    version: 'runtime-1',
    targetModule: draft.viewer_manifest.robotId,
    estimatedTime: Math.max(steps.length * 90, 300),
    difficulty: 'beginner',
    steps,
  }
}
