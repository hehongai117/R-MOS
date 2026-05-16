import { useMemo } from 'react'
import { Slider } from 'antd'
import type { AssemblyJoint } from './useAssemblyManifest'

interface JointControlPanelProps {
  joints: AssemblyJoint[]
  jointAngles: Record<string, number>
  onJointChange: (linkName: string, angle: number) => void
  onReset: () => void
}

interface JointGroup {
  label: string
  joints: AssemblyJoint[]
}

export function JointControlPanel({
  joints,
  jointAngles,
  onJointChange,
  onReset,
}: JointControlPanelProps) {
  // Only show movable joints (not fixed)
  const movableJoints = useMemo(
    () => joints.filter((j) => j.type !== 'fixed'),
    [joints],
  )

  const groups = useMemo(() => groupJoints(movableJoints), [movableJoints])

  if (movableJoints.length === 0) return null

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium" style={{ color: 'var(--text-primary, #e0e0e0)' }}>
          关节控制
        </h3>
        <button
          onClick={onReset}
          className="text-xs hover:opacity-80 transition-opacity cursor-pointer bg-transparent border-none"
          style={{ color: 'var(--text-secondary, #999)' }}
        >
          重置
        </button>
      </div>
      <div className="overflow-y-auto" style={{ maxHeight: '60vh' }}>
        <div className="space-y-4 pr-2">
          {groups.map((group) => (
            <div key={group.label}>
              <div
                className="text-[11px] font-medium uppercase tracking-wider mb-2"
                style={{ color: 'var(--text-muted, #666)' }}
              >
                {group.label}
              </div>
              <div className="space-y-2">
                {group.joints.map((joint) => {
                  const lower = joint.limits?.lower ?? -Math.PI
                  const upper = joint.limits?.upper ?? Math.PI
                  const current = jointAngles[joint.child_link] ?? 0
                  return (
                    <div key={joint.name} className="space-y-0">
                      <div className="flex justify-between text-xs">
                        <span
                          className="truncate max-w-[140px]"
                          style={{ color: 'var(--text-secondary, #999)' }}
                        >
                          {humanizeJointName(joint.name)}
                        </span>
                        <span
                          className="font-mono"
                          style={{ color: 'var(--text-muted, #666)' }}
                        >
                          {(current * 180 / Math.PI).toFixed(0)}°
                        </span>
                      </div>
                      <Slider
                        min={lower}
                        max={upper}
                        step={0.01}
                        value={current}
                        onChange={(val) => onJointChange(joint.child_link, val)}
                        tooltip={{ formatter: (val) => val ? `${(val * 180 / Math.PI).toFixed(1)}°` : '0°' }}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function groupJoints(joints: AssemblyJoint[]): JointGroup[] {
  const groups: Record<string, AssemblyJoint[]> = {}

  for (const joint of joints) {
    const label = detectGroup(joint.name)
    if (!groups[label]) groups[label] = []
    groups[label].push(joint)
  }

  return Object.entries(groups).map(([label, items]) => ({ label, joints: items }))
}

function detectGroup(name: string): string {
  const n = name.toLowerCase()
  if (n.includes('left') && n.includes('arm')) return '左臂'
  if (n.includes('right') && n.includes('arm')) return '右臂'
  if (n.includes('left') && (n.includes('thigh') || n.includes('knee') || n.includes('foot') || n.includes('shank') || n.includes('ankle'))) return '左腿'
  if (n.includes('right') && (n.includes('thigh') || n.includes('knee') || n.includes('foot') || n.includes('shank') || n.includes('ankle'))) return '右腿'
  if (n.includes('waist') || n.includes('torso')) return '躯干'
  if (n.includes('head') || n.includes('neck') || n.includes('camera')) return '头部'
  return '其他'
}

function humanizeJointName(name: string): string {
  return name
    .replace(/_joint$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
