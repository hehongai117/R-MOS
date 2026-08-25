import { useGLTF } from '@react-three/drei'
import type { GLTFLoader } from 'three-stdlib'

import { getAccessToken } from '@/store/authStore'

type Path = string | string[]
type UseDraco = boolean | string
type UseMeshopt = boolean
type AuthedGLTFResult<T extends Path> = ReturnType<typeof useGLTF<T>>

interface UseAuthedGLTF {
  <T extends Path>(
    path: T,
    useDraco?: UseDraco,
    useMeshopt?: UseMeshopt,
  ): AuthedGLTFResult<T>
  preload(path: Path, useDraco?: UseDraco, useMeshopt?: UseMeshopt): undefined
}

function extendLoader(loader: GLTFLoader): void {
  const token = getAccessToken()
  if (token) {
    loader.setRequestHeader({ Authorization: `Bearer ${token}` })
  }
}

function loadAuthedGLTF<T extends Path>(
  path: T,
  useDraco?: UseDraco,
  useMeshopt?: UseMeshopt,
): AuthedGLTFResult<T> {
  return useGLTF(path, useDraco, useMeshopt, extendLoader)
}

export const useAuthedGLTF: UseAuthedGLTF = Object.assign(loadAuthedGLTF, {
  preload(path: Path, useDraco?: UseDraco, useMeshopt?: UseMeshopt): undefined {
    return useGLTF.preload(path, useDraco, useMeshopt, extendLoader)
  },
})
