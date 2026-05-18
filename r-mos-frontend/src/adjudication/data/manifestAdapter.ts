import type {
  RobotDataManifest,
  ManifestPartEntry,
  ManifestScrewEntry,
  ManifestConstraintEntry,
} from '@/components/Viewer3D/assemblyManifest'
import type {
  Part,
  Constraint,
  ConstraintType,
  ScrewSpec,
} from '../types/adjudication'
import { PartCategory } from '../types/adjudication'

const CATEGORY_MAP: Record<string, PartCategory> = {
  frame: PartCategory.FRAME,
  cover: PartCategory.COVER,
  screw: PartCategory.SCREW,
  nut: PartCategory.NUT,
  motor: PartCategory.MOTOR,
  bearing: PartCategory.BEARING,
  pcb: PartCategory.PCB,
  wire: PartCategory.WIRE,
  tool: PartCategory.TOOL,
}

export function manifestPartToPart(entry: ManifestPartEntry, modelBase: string): Part {
  return {
    id: entry.id,
    category: CATEGORY_MAP[entry.category] ?? PartCategory.FRAME,
    bomCode: entry.bom_code,
    displayName: entry.display_name,
    modelPath: entry.mesh_id ? `${modelBase}/${entry.mesh_id}` : '',
    parentId: entry.parent_id ?? undefined,
    localPosition: entry.local_position,
    localRotation: entry.local_rotation,
  }
}

export function manifestScrewToPart(entry: ManifestScrewEntry, modelBase: string): Part {
  const screwSpec: ScrewSpec = {
    type: entry.spec.type,
    pitch: entry.spec.pitch,
    threadLength: entry.spec.thread_length,
    requiredTool: entry.spec.required_tool,
    torque: entry.spec.torque_nm,
  }
  return {
    id: entry.id,
    category: PartCategory.SCREW,
    bomCode: entry.bom_code,
    displayName: entry.spec.type,
    modelPath: '',
    parentId: entry.parent_id,
    localPosition: entry.position,
    localRotation: [0, 0, 0],
    screwSpec,
  }
}

export function manifestConstraintToConstraint(entry: ManifestConstraintEntry): Constraint {
  return {
    id: entry.id,
    type: entry.type as ConstraintType,
    constrainedPart: entry.constrained_part,
    constrainingPart: entry.constraining_part,
    params: entry.params as any,
    releaseCondition: {
      type: entry.release_condition.type as any,
      requiredActions: entry.release_condition.required_actions as any,
    },
    isActive: true,
  }
}

/** 从 RobotDataManifest 构建完整的 adjudication 数据集 */
export function buildAdjudicationDataFromManifest(manifest: RobotDataManifest) {
  const modelBase = `/api/v1/robots/${manifest.robotId}/assets`

  const partRegistry: Record<string, Part> = {}
  for (const entry of manifest.parts_registry ?? []) {
    partRegistry[entry.id] = manifestPartToPart(entry, modelBase)
  }

  const screwRegistry: Record<string, Part> = {}
  for (const entry of manifest.screw_instances ?? []) {
    screwRegistry[entry.id] = manifestScrewToPart(entry, modelBase)
  }

  const constraints: Constraint[] = (manifest.constraints ?? []).map(manifestConstraintToConstraint)

  return { partRegistry, screwRegistry, constraints }
}
