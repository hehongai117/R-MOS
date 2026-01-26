/**
 * 幽灵手引导解析工具
 */
import type { SOPStep } from '@/types/sop'

const TARGET_PART_MAP: Record<string, string> = {
  torso_link: 'torso_link',
  torso: 'torso_link',
  base_link: 'base_link',
  left_knee: 'left_knee_link',
  right_knee: 'right_knee_link',
  knee_left: 'left_knee_link',
  knee_right: 'right_knee_link',
  left_arm: 'left_arm_yaw_link',
  right_arm: 'right_arm_yaw_link',
  left_leg: 'left_thigh_pitch_link',
  right_leg: 'right_thigh_pitch_link',
}

export function resolveTargetPart(step?: SOPStep | null): string | null {
  if (!step?.target_part) return null
  const raw = step.target_part.toLowerCase()

  if (TARGET_PART_MAP[raw]) {
    return TARGET_PART_MAP[raw]
  }

  if (raw.includes('knee') && raw.includes('right')) return 'right_knee_link'
  if (raw.includes('knee') && raw.includes('left')) return 'left_knee_link'
  if (raw.includes('torso')) return 'torso_link'
  if (raw.includes('arm') && raw.includes('left')) return 'left_arm_yaw_link'
  if (raw.includes('arm') && raw.includes('right')) return 'right_arm_yaw_link'
  if (raw.includes('leg') && raw.includes('left')) return 'left_thigh_pitch_link'
  if (raw.includes('leg') && raw.includes('right')) return 'right_thigh_pitch_link'

  return null
}

export function resolveToolLabel(step?: SOPStep | null): string {
  if (!step) return '通用工具'
  if (step.tools_required && step.tools_required.length > 0) {
    return step.tools_required[0]
  }
  return step.expected_action ? `动作：${step.expected_action}` : '通用工具'
}
