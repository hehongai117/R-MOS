import { Suspense, useEffect, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Center } from '@react-three/drei'
import { RuntimeAssetPreview } from './RuntimeAssetPreview'
import apiClient, { API_BASE_URL } from '@/api/client'

interface GLBAsset {
  id: number
  file_path: string
  file_name: string
  asset_type: string
}

interface RobotGLBViewerProps {
  robotId: number
  width?: string | number
  height?: string | number
  backgroundColor?: string
}

export function RobotGLBViewer({
  robotId,
  width = '100%',
  height = '600px',
  backgroundColor = '#0a1929',
}: RobotGLBViewerProps) {
  const [glbAssets, setGlbAssets] = useState<GLBAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetchAssets() {
      setLoading(true)
      setError(null)
      try {
        const res = await apiClient.get<{ items: GLBAsset[] } | GLBAsset[]>(
          `/robots/${robotId}/assets`,
          { params: { asset_type: 'model_glb' } }
        )
        if (!cancelled) {
          const data = res.data
          const items = Array.isArray(data) ? data : (data as { items: GLBAsset[] }).items ?? []
          setGlbAssets(items)
        }
      } catch {
        if (!cancelled) {
          setError('加载 3D 模型列表失败')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void fetchAssets()
    return () => {
      cancelled = true
    }
  }, [robotId])

  const containerStyle: React.CSSProperties = {
    width,
    height: height as string | number,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: backgroundColor,
    borderRadius: 8,
  }

  if (loading) {
    return (
      <div style={containerStyle}>
        <span style={{ color: '#8899aa' }}>加载 3D 模型中...</span>
      </div>
    )
  }

  if (error || glbAssets.length === 0) {
    return (
      <div style={containerStyle}>
        <span style={{ color: '#8899aa' }}>{error ?? '该机器人暂无 3D 模型'}</span>
      </div>
    )
  }

  return (
    <div style={{ width, height, borderRadius: 8, overflow: 'hidden' }}>
      <Canvas
        camera={{ position: [2, 1.5, 2], fov: 45 }}
        style={{ background: backgroundColor }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <Suspense fallback={null}>
          <Center>
            {glbAssets.map((asset) => {
              // file_path 格式：{robotId}/filename.glb，去掉第一段
              const relativePath = asset.file_path.split('/').slice(1).join('/')
              const assetUrl = `${API_BASE_URL}/api/v1/robots/${robotId}/assets/${relativePath}`
              return (
                <RuntimeAssetPreview
                  key={asset.id}
                  assetUrl={assetUrl}
                  assetPath={asset.file_path}
                />
              )
            })}
          </Center>
        </Suspense>
        <OrbitControls makeDefault />
        <gridHelper args={[10, 10, '#1a3a5c', '#1a3a5c']} />
      </Canvas>
    </div>
  )
}
