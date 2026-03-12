import { useGLTF } from '@react-three/drei'
import { useEffect, useMemo, useState } from 'react'
import { Mesh, MeshStandardMaterial, type Object3D } from 'three'
import { ColladaLoader } from 'three/examples/jsm/loaders/ColladaLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { VRMLLoader } from 'three/examples/jsm/loaders/VRMLLoader.js'

import apiClient from '@/api/client'
import { detectRuntimeAssetFormat } from '@/components/Viewer3D/runtimeManifest'
import {
  centerObjectAtOrigin,
  type VisibleBounds,
} from '@/components/Viewer3D/viewerBounds'

interface RuntimeAssetPreviewProps {
  assetUrl: string | null
  assetPath?: string | null
  onVisibleBoundsChange?: (bounds: VisibleBounds) => void
}

export function RuntimeAssetPreview({
  assetUrl,
  assetPath,
  onVisibleBoundsChange,
}: RuntimeAssetPreviewProps) {
  if (!assetUrl) {
    return <RuntimeAssetFallback />
  }

  return (
    <RuntimeAssetModel
      assetUrl={assetUrl}
      assetPath={assetPath ?? assetUrl}
      onVisibleBoundsChange={onVisibleBoundsChange}
    />
  )
}

function RuntimeAssetFallback() {
  return (
    <mesh>
      <boxGeometry args={[0.6, 0.6, 0.6]} />
      <meshStandardMaterial color="#4fc3f7" wireframe />
    </mesh>
  )
}

function RuntimeAssetModel({
  assetUrl,
  assetPath,
  onVisibleBoundsChange,
}: {
  assetUrl: string
  assetPath: string
  onVisibleBoundsChange?: (bounds: VisibleBounds) => void
}) {
  const assetFormat = detectRuntimeAssetFormat(assetPath)
  const [resolvedAssetUrl, setResolvedAssetUrl] = useState<string | null>(null)
  const [assetBlob, setAssetBlob] = useState<Blob | null>(null)

  useEffect(() => {
    let ignore = false
    let objectUrl: string | null = null

    const loadAsset = async () => {
      const response = await apiClient.get<Blob>(assetUrl, {
        baseURL: '',
        responseType: 'blob',
      })
      if (assetFormat === 'gltf') {
        objectUrl = URL.createObjectURL(response.data)
      }
      if (!ignore) {
        setAssetBlob(response.data)
        setResolvedAssetUrl(objectUrl)
      }
    }

    void loadAsset().catch(() => {
      if (!ignore) {
        setAssetBlob(null)
        setResolvedAssetUrl(null)
      }
    })

    return () => {
      ignore = true
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [assetFormat, assetUrl])

  if (assetFormat === 'unsupported') {
    return <RuntimeAssetFallback />
  }
  if (assetFormat === 'gltf') {
    if (!resolvedAssetUrl) {
      return <RuntimeAssetFallback />
    }
    return (
      <LoadedRuntimeGltfAsset
        assetUrl={resolvedAssetUrl}
        onVisibleBoundsChange={onVisibleBoundsChange}
      />
    )
  }
  if (!assetBlob) {
    return <RuntimeAssetFallback />
  }
  return (
    <LoadedRuntimeMeshAsset
      assetBlob={assetBlob}
      assetFormat={assetFormat}
      onVisibleBoundsChange={onVisibleBoundsChange}
    />
  )
}

function LoadedRuntimeGltfAsset({
  assetUrl,
  onVisibleBoundsChange,
}: {
  assetUrl: string
  onVisibleBoundsChange?: (bounds: VisibleBounds) => void
}) {
  const gltf = useGLTF(assetUrl)
  const centeredAsset = useMemo(() => centerObjectAtOrigin(gltf.scene.clone()), [gltf.scene])

  useEffect(() => {
    if (!centeredAsset.bounds) return
    onVisibleBoundsChange?.(centeredAsset.bounds)
  }, [centeredAsset.bounds, onVisibleBoundsChange])

  return <primitive object={centeredAsset.object} />
}

function LoadedRuntimeMeshAsset({
  assetBlob,
  assetFormat,
  onVisibleBoundsChange,
}: {
  assetBlob: Blob
  assetFormat: Exclude<ReturnType<typeof detectRuntimeAssetFormat>, 'gltf' | 'unsupported'>
  onVisibleBoundsChange?: (bounds: VisibleBounds) => void
}) {
  const [parsedObject, setParsedObject] = useState<{
    object: Object3D
    bounds: VisibleBounds | null
  } | null>(null)

  useEffect(() => {
    let ignore = false

    const parseAsset = async () => {
      const nextObject = centerObjectAtOrigin(await parseRuntimeAssetBlob(assetBlob, assetFormat))
      if (!ignore) {
        setParsedObject(nextObject)
      }
    }

    void parseAsset().catch(() => {
      if (!ignore) {
        setParsedObject(null)
      }
    })

    return () => {
      ignore = true
    }
  }, [assetBlob, assetFormat])

  if (!parsedObject) {
    return <RuntimeAssetFallback />
  }

  return <LoadedParsedRuntimeMesh parsedObject={parsedObject.object} bounds={parsedObject.bounds} onVisibleBoundsChange={onVisibleBoundsChange} />
}

function LoadedParsedRuntimeMesh({
  parsedObject,
  bounds,
  onVisibleBoundsChange,
}: {
  parsedObject: Object3D
  bounds: VisibleBounds | null
  onVisibleBoundsChange?: (bounds: VisibleBounds) => void
}) {
  useEffect(() => {
    if (!bounds) return
    onVisibleBoundsChange?.(bounds)
  }, [bounds, onVisibleBoundsChange])

  return <primitive object={parsedObject} />
}

async function parseRuntimeAssetBlob(
  assetBlob: Blob,
  assetFormat: Exclude<ReturnType<typeof detectRuntimeAssetFormat>, 'gltf' | 'unsupported'>,
): Promise<Object3D> {
  if (assetFormat === 'stl') {
    const geometry = new STLLoader().parse(await assetBlob.arrayBuffer())
    geometry.computeVertexNormals()
    return new Mesh(
      geometry,
      new MeshStandardMaterial({
        color: '#9bd7ff',
        metalness: 0.1,
        roughness: 0.7,
      }),
    )
  }
  if (assetFormat === 'obj') {
    return new OBJLoader().parse(await assetBlob.text())
  }
  if (assetFormat === 'dae') {
    return new ColladaLoader().parse(await assetBlob.text(), '').scene
  }
  return new VRMLLoader().parse(await assetBlob.text(), '')
}
