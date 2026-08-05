import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { useAssemblyManifest } from '../useAssemblyManifest'

const mockGet = vi.fn()
vi.mock('@/api/client', () => ({
  apiClient: { get: (...args: unknown[]) => mockGet(...args) },
}))

const manifestFor = (rootId: string, links: string[]) => ({
  data: {
    version: '2026-05-16',
    robotId: rootId,
    rootNodeId: links[0],
    mesh_catalog: Object.fromEntries(
      links.map((l) => [`${l}_mesh`, `models/${l}.glb`]),
    ),
    nodes: links.map((l) => ({ id: l, mesh_id: `${l}_mesh` })),
    joints: [],
  },
})

describe('useAssemblyManifest', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('loads the manifest for the given robot', async () => {
    mockGet.mockResolvedValue(manifestFor('1', ['base_link', 'torso_link']))

    const { result } = renderHook(() => useAssemblyManifest(1))

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.manifest?.rootNodeId).toBe('base_link')
    expect(Object.keys(result.current.manifest!.mesh_catalog)).toHaveLength(2)
  })

  it('clears the previous robot manifest while switching robots', async () => {
    // 回归用例：切换机型时若不清空旧 manifest，渲染层会用「旧机型的 link 名 +
    // 新机型的 robotId」去请求 GLB，导致一批 404（实测切到 W2V1 时出现 23 个）。
    // 注意：manifestCache 是模块级的，跨用例不会重置，这里用独立的 robotId 避免污染
    mockGet.mockResolvedValueOnce(manifestFor('201', ['base_link', 'torso_link']))

    const { result, rerender } = renderHook(
      ({ id }) => useAssemblyManifest(id),
      { initialProps: { id: 201 } },
    )
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.manifest?.rootNodeId).toBe('base_link')

    // 新机型的请求悬挂未决，模拟网络往返窗口
    let resolveSecond: ((v: unknown) => void) | undefined
    mockGet.mockImplementationOnce(
      () => new Promise((res) => { resolveSecond = res }),
    )
    rerender({ id: 202 })

    // 关键断言：请求未完成时不能还持有 1 号机的 manifest
    await waitFor(() => {
      expect(result.current.manifest).toBeNull()
    })

    resolveSecond?.(manifestFor('202', ['pelvis_link']))
    await waitFor(() => expect(result.current.manifest?.rootNodeId).toBe('pelvis_link'))
  })

  it('treats a missing manifest as "no assembly view" rather than an error', async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } })

    const { result } = renderHook(() => useAssemblyManifest(1234))

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.manifest).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.hasManifest).toBe(false)
  })
})

describe('useAssemblyManifest — render-phase safety', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('never exposes a manifest belonging to a different robot, even before effects run', async () => {
    // 回归用例：React 先渲染后跑 effect。robotId 一变，渲染这一帧若仍返回上一台的
    // manifest，子组件就会用「新 robotId + 旧 link 名」发请求 —— 实测切换机型时
    // 产生 29 个 404。因此必须在渲染期就按 robotId 校验，不能只在 effect 里清空。
    mockGet.mockResolvedValueOnce(manifestFor('301', ['base_link', 'torso_link']))

    const { result, rerender } = renderHook(
      ({ id }) => useAssemblyManifest(id),
      { initialProps: { id: 301 } },
    )
    await waitFor(() => expect(result.current.manifest?.rootNodeId).toBe('base_link'))

    mockGet.mockImplementationOnce(() => new Promise(() => {}))
    rerender({ id: 302 })

    // 同步断言：不等待任何 effect/异步，此刻就不能再有 301 的 manifest
    expect(result.current.manifest).toBeNull()
  })
})
