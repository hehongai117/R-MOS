import { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { Center, OrbitControls, Environment } from '@react-three/drei'
import { Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'

import { useAssemblyManifest } from './useAssemblyManifest'
import { ManifestDrivenRenderer } from './ManifestDrivenRenderer'
import { RobotGLBViewer } from './RobotGLBViewer'

interface MonitorRobotViewerProps {
  robotId: number
  height?: number | string
  jointAngles?: Record<string, number>
  highlightLinks?: string[]
}

/**
 * Simplified 3D viewer for the monitor page.
 * Uses ManifestDrivenRenderer when a manifest is available,
 * falls back to RobotGLBViewer otherwise.
 * Accepts external jointAngles and highlightLinks from WebSocket telemetry.
 */
export function MonitorRobotViewer({
  robotId,
  height = 460,
  jointAngles = {},
  highlightLinks = [],
}: MonitorRobotViewerProps) {
  const { manifest, loading, hasManifest } = useAssemblyManifest(robotId)

  if (loading) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin indicator={<LoadingOutlined spin />} size="large" />
        <span className="ml-3 text-sm" style={{ color: '#999' }}>加载 3D 模型...</span>
      </div>
    )
  }

  if (!hasManifest || !manifest) {
    return <RobotGLBViewer robotId={robotId} height={height} />
  }

  return (
    <div style={{ width: '100%', height }}>
      <Canvas
        camera={{ position: [1.5, 1, 1.5], fov: 45 }}
        style={{ background: '#08101f' }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <directionalLight position={[-5, 3, -5]} intensity={0.4} />
        <Suspense fallback={null}>
          <Center>
            <ManifestDrivenRenderer
              manifest={manifest}
              robotId={robotId}
              jointAngles={jointAngles}
              highlightLinks={highlightLinks}
            />
          </Center>
        </Suspense>
        <OrbitControls enablePan enableZoom enableRotate />
        <Environment preset="studio" />
      </Canvas>
    </div>
  )
}
