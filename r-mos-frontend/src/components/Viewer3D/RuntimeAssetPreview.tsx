import { Center, Clone, useGLTF } from '@react-three/drei'
import { useEffect, useMemo, useState } from 'react'
import { Mesh, MeshStandardMaterial, type Object3D } from 'three'
import { ColladaLoader } from 'three/examples/jsm/loaders/ColladaLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { VRMLLoader } from 'three/examples/jsm/loaders/VRMLLoader.js'

import apiClient from '@/api/client'
import { detectRuntimeAssetFormat } from '@/components/Viewer3D/runtimeManifest'

interface RuntimeAssetPreviewProps {
  assetUrl: string | null
  assetPath?: string | null
}

export function RuntimeAssetPreview({ assetUrl, assetPath }: RuntimeAssetPreviewProps) {
  if (!assetUrl) {
    return <RuntimeAssetFallback />
  }

  return <RuntimeAssetModel assetUrl={assetUrl} assetPath={assetPath ?? assetUrl} />
}

function RuntimeAssetFallback() {
  return (
    <mesh>
      <boxGeometry args={[0.6, 0.6, 0.6]} />
      <meshStandardMaterial color="#4fc3f7" wireframe />
    </mesh>
  )
}

function RuntimeAssetModel({ assetUrl, assetPath }: { assetUrl: string; assetPath: string }) {
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
    return <LoadedRuntimeGltfAsset assetUrl={resolvedAssetUrl} />
  }
  if (!assetBlob) {
    return <RuntimeAssetFallback />
  }
  return <LoadedRuntimeMeshAsset assetBlob={assetBlob} assetFormat={assetFormat} />
}

function LoadedRuntimeGltfAsset({ assetUrl }: { assetUrl: string }) {
  const gltf = useGLTF(assetUrl)
  const scene = useMemo(() => gltf.scene.clone(), [gltf.scene])

  return (
    <Center>
      <Clone object={scene} />
    </Center>
  )
}

function LoadedRuntimeMeshAsset({ assetBlob, assetFormat }: { assetBlob: Blob; assetFormat: Exclude<ReturnType<typeof detectRuntimeAssetFormat>, 'gltf' | 'unsupported'> }) {
  const [parsedObject, setParsedObject] = useState<Object3D | null>(null)

  useEffect(() => {
    let ignore = false

    const parseAsset = async () => {
      const nextObject = await parseRuntimeAssetBlob(assetBlob, assetFormat)
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

  return (
    <Center>
      <primitive object={parsedObject} />
    </Center>
  )
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
