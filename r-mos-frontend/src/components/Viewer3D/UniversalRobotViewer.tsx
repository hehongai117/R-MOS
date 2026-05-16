import { Suspense, useCallback, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { Center, OrbitControls, Environment } from '@react-three/drei'
import { Slider, Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'

import { useAssemblyManifest } from './useAssemblyManifest'
import { ManifestDrivenRenderer } from './ManifestDrivenRenderer'
import { JointControlPanel } from './JointControlPanel'
import { RobotGLBViewer } from './RobotGLBViewer'

interface UniversalRobotViewerProps {
  robotId: number
  robotName?: string
}

export function UniversalRobotViewer({ robotId, robotName }: UniversalRobotViewerProps) {
  const { manifest, loading, hasManifest } = useAssemblyManifest(robotId)
  const [jointAngles, setJointAngles] = useState<Record<string, number>>({})
  const [explodeDistance, setExplodeDistance] = useState(0)

  const handleJointChange = useCallback((linkName: string, angle: number) => {
    setJointAngles((prev) => ({ ...prev, [linkName]: angle }))
  }, [])

  const handleReset = useCallback(() => {
    setJointAngles({})
    setExplodeDistance(0)
  }, [])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spin indicator={<LoadingOutlined spin />} size="large" />
        <span className="ml-3 text-sm" style={{ color: 'var(--text-secondary, #999)' }}>
          加载 3D 模型...
        </span>
      </div>
    )
  }

  // No assembly manifest → fallback to GLB grid viewer
  if (!hasManifest || !manifest) {
    return <RobotGLBViewer robotId={robotId} height="100%" />
  }

  // Full assembly viewer with joint controls
  const hasJoints = manifest.joints && manifest.joints.filter((j) => j.type !== 'fixed').length > 0

  return (
    <div className="flex h-full gap-0">
      {/* Left panel: joint controls */}
      {hasJoints && (
        <div
          className="w-[240px] shrink-0 border-r p-4 overflow-y-auto"
          style={{
            borderColor: 'var(--border-subtle, #2a2a3a)',
            background: 'var(--bg-surface, #12121a)',
          }}
        >
          <JointControlPanel
            joints={manifest.joints!}
            jointAngles={jointAngles}
            onJointChange={handleJointChange}
            onReset={handleReset}
          />
          <div className="mt-6 space-y-2">
            <div className="flex justify-between text-xs">
              <span style={{ color: 'var(--text-secondary, #999)' }}>拆解视图</span>
              <span className="font-mono" style={{ color: 'var(--text-muted, #666)' }}>
                {(explodeDistance * 100).toFixed(0)}%
              </span>
            </div>
            <Slider
              min={0}
              max={2}
              step={0.01}
              value={explodeDistance}
              onChange={(val) => setExplodeDistance(val)}
              tooltip={{ formatter: (val) => val ? `${(val * 100).toFixed(0)}%` : '0%' }}
            />
          </div>
        </div>
      )}

      {/* Main 3D viewport */}
      <div className="flex-1 relative">
        <Canvas
          camera={{ position: [2, 2, 2], fov: 50 }}
          style={{ background: '#0a0a0f' }}
        >
          <ambientLight intensity={0.4} />
          <directionalLight position={[5, 10, 5]} intensity={0.8} />
          <directionalLight position={[-5, -5, -5]} intensity={0.3} />
          <Suspense fallback={null}>
            <Center>
              <ManifestDrivenRenderer
                manifest={manifest}
                robotId={robotId}
                jointAngles={jointAngles}
                explodeDistance={explodeDistance}
              />
            </Center>
          </Suspense>
          <OrbitControls enablePan enableZoom enableRotate />
          <Environment preset="studio" />
        </Canvas>
        {/* Robot name overlay */}
        {robotName && (
          <div
            className="absolute top-4 left-4 rounded-md px-3 py-1.5 backdrop-blur text-sm"
            style={{
              background: 'rgba(18, 18, 26, 0.8)',
              color: 'var(--text-primary, #e0e0e0)',
            }}
          >
            {robotName} — 3D 展示
          </div>
        )}
      </div>
    </div>
  )
}
