/**
 * AUTH-GATE 前端面：3D 资产必须带令牌加载。
 *
 * 背景：Phase 3 第 1 批的默认拒绝网关（`app/core/public_routes.py` +
 * `enforce_authenticated`）生效后，`/api/v1/robots/{id}/assets/*` 一律要求认证。
 * 而 `@react-three/drei` 的 `useGLTF` 内部用 `GLTFLoader` 直接发请求，
 * 既不走 `apiClient`、也不带 `Authorization` 头，因此 3D 网格加载全部 401。
 *
 * 本文件锁定两件事：
 *   1. 存在唯一的带令牌加载封装 `useAuthedGLTF`，它把 `Authorization` 头
 *      注入 `GLTFLoader`（drei 9.x 的 `useGLTF` 第 4 参数 `extendLoader`）；
 *   2. `Viewer3D/` 下除该封装外，**任何文件都不得**再直接 import `useGLTF`，
 *      也不得再用裸 `fetch` 取后端资产 —— 防止以后新增组件重新踩同一个坑。
 *
 * 门禁语义在断言里，不要为了让测试变绿而放宽断言。
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AUTH_STORAGE_KEYS, useAuthStore } from '@/store/authStore'

const useGLTFMock = vi.hoisted(() => {
  const fn = vi.fn(() => ({ scene: {}, nodes: {}, materials: {} }))
  return Object.assign(fn, { preload: vi.fn(), clear: vi.fn() })
})

vi.mock('@react-three/drei', () => ({ useGLTF: useGLTFMock }))

const VIEWER_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
/** 唯一允许直接接触 drei `useGLTF` 的文件 */
const WRAPPER_BASENAME = 'useAuthedGLTF.ts'

function collectSourceFiles(dir: string): string[] {
  const out: string[] = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === '__tests__' || entry.name === 'node_modules') continue
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      out.push(...collectSourceFiles(full))
    } else if (/\.tsx?$/.test(entry.name)) {
      out.push(full)
    }
  }
  return out
}

/** 取出 extendLoader（useGLTF 的第 4 参数），并用假 loader 观察它注入了什么头 */
function captureRequestHeader(callIndex = 0): Record<string, string> | null {
  const extendLoader = useGLTFMock.mock.calls[callIndex]?.[3] as
    | ((loader: unknown) => void)
    | undefined
  if (typeof extendLoader !== 'function') return null
  let captured: Record<string, string> | null = null
  extendLoader({
    setRequestHeader: (headers: Record<string, string>) => {
      captured = headers
    },
  })
  return captured
}

describe('useAuthedGLTF：带令牌的 GLB 加载封装', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({ accessToken: null })
    useGLTFMock.mockClear()
    useGLTFMock.preload.mockClear()
  })

  it('把 store 中的 access token 注入 GLTFLoader 的 Authorization 头', async () => {
    const { useAuthedGLTF } = await import('../useAuthedGLTF')
    useAuthStore.setState({ accessToken: 'store-token-abc' })

    useAuthedGLTF('/api/v1/robots/1/assets/models/base_link.glb')

    expect(useGLTFMock).toHaveBeenCalledTimes(1)
    expect(useGLTFMock.mock.calls[0][0]).toBe('/api/v1/robots/1/assets/models/base_link.glb')
    expect(captureRequestHeader()).toEqual({ Authorization: 'Bearer store-token-abc' })
  })

  it('store 为空时回落到 localStorage，与 apiClient 的令牌口径一致', async () => {
    const { useAuthedGLTF } = await import('../useAuthedGLTF')
    localStorage.setItem(AUTH_STORAGE_KEYS.accessToken, 'ls-token-xyz')

    useAuthedGLTF('/api/v1/robots/1/assets/models/base_link.glb')

    expect(captureRequestHeader()).toEqual({ Authorization: 'Bearer ls-token-xyz' })
  })

  it('完全没有令牌时不设头，也不抛异常（匿名场景由后端 401 兜底）', async () => {
    const { useAuthedGLTF } = await import('../useAuthedGLTF')

    expect(() => useAuthedGLTF('/api/v1/robots/1/assets/models/base_link.glb')).not.toThrow()
    expect(captureRequestHeader()).toBeNull()
  })

  it('支持数组形式（SubPartsGroup 一次加载多个 mesh）', async () => {
    const { useAuthedGLTF } = await import('../useAuthedGLTF')
    useAuthStore.setState({ accessToken: 'store-token-abc' })

    useAuthedGLTF(['/a.glb', '/b.glb'])

    expect(useGLTFMock.mock.calls[0][0]).toEqual(['/a.glb', '/b.glb'])
    expect(captureRequestHeader()).toEqual({ Authorization: 'Bearer store-token-abc' })
  })

  it('preload 同样带令牌（ModelPreloader 预热走的是这条路径）', async () => {
    const { useAuthedGLTF } = await import('../useAuthedGLTF')
    useAuthStore.setState({ accessToken: 'store-token-abc' })

    useAuthedGLTF.preload('/api/v1/robots/1/assets/models/base_link.glb')

    expect(useGLTFMock.preload).toHaveBeenCalledTimes(1)
    const extendLoader = useGLTFMock.preload.mock.calls[0][3] as (loader: unknown) => void
    let captured: Record<string, string> | null = null
    extendLoader({
      setRequestHeader: (headers: Record<string, string>) => {
        captured = headers
      },
    })
    expect(captured).toEqual({ Authorization: 'Bearer store-token-abc' })
  })
})

describe('架构门禁：Viewer3D 下不得绕开带令牌封装', () => {
  it('除 useAuthedGLTF.ts 外，没有任何文件直接 import drei 的 useGLTF', () => {
    const offenders = collectSourceFiles(VIEWER_DIR)
      .filter((file) => path.basename(file) !== WRAPPER_BASENAME)
      .filter((file) => {
        const src = fs.readFileSync(file, 'utf8')
        return /import\s*\{[^}]*\buseGLTF\b[^}]*\}\s*from\s*['"]@react-three\/drei['"]/.test(src)
      })
      .map((file) => path.relative(VIEWER_DIR, file))

    expect(offenders).toEqual([])
  })

  it('没有任何文件用裸 fetch 取后端资产（必须走 apiClient 或带令牌封装）', () => {
    const offenders = collectSourceFiles(VIEWER_DIR)
      .filter((file) => {
        const src = fs.readFileSync(file, 'utf8')
        return /(^|[^.\w])fetch\s*\(/m.test(src)
      })
      .map((file) => path.relative(VIEWER_DIR, file))

    expect(offenders).toEqual([])
  })
})
