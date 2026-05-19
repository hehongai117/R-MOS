import { renderHook, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useSOPScripts } from '../useSOPScripts'
import type { SOPScriptAdjudication } from '@/adjudication/types/adjudication'

vi.mock('@/api/sopScripts', () => ({
  fetchAdjudicationSOPs: vi.fn(),
}))

import { fetchAdjudicationSOPs } from '@/api/sopScripts'

const mockedFetch = fetchAdjudicationSOPs as ReturnType<typeof vi.fn>

const mockSOP: SOPScriptAdjudication = {
  sopId: 'SOP-001',
  title: 'Test SOP',
  version: '1.0',
  targetModule: 'module-a',
  estimatedTime: 120,
  difficulty: 'beginner',
  steps: [],
}

describe('useSOPScripts', () => {
  beforeEach(() => {
    mockedFetch.mockReset()
  })

  it('挂载后从 API 加载 SOP 脚本，成功时设置 fromApi=true', async () => {
    mockedFetch.mockResolvedValueOnce([mockSOP])

    const { result } = renderHook(() => useSOPScripts())

    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.scripts).toEqual([mockSOP])
    expect(result.current.fromApi).toBe(true)
  })

  it('传入 robotModelId 时调用 API 带 { robot_model_id }', async () => {
    mockedFetch.mockResolvedValueOnce([mockSOP])

    const { result } = renderHook(() => useSOPScripts(42))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockedFetch).toHaveBeenCalledWith({ robot_model_id: 42 })
    expect(result.current.scripts).toEqual([mockSOP])
  })

  it('无 robotModelId 时调用 API 传 undefined', async () => {
    mockedFetch.mockResolvedValueOnce([])

    const { result } = renderHook(() => useSOPScripts())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockedFetch).toHaveBeenCalledWith(undefined)
  })

  it('无 robotModelId (null) 时调用 API 传 undefined', async () => {
    mockedFetch.mockResolvedValueOnce([])

    const { result } = renderHook(() => useSOPScripts(null))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockedFetch).toHaveBeenCalledWith(undefined)
  })

  it('API 失败时返回空数组，fromApi 保持 false', async () => {
    mockedFetch.mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useSOPScripts())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.scripts).toEqual([])
    expect(result.current.fromApi).toBe(false)
  })

  it('robotModelId 变化时重新请求', async () => {
    mockedFetch.mockResolvedValueOnce([mockSOP])
    mockedFetch.mockResolvedValueOnce([{ ...mockSOP, sopId: 'SOP-002' }])

    const { result, rerender } = renderHook(
      ({ id }: { id?: number | null }) => useSOPScripts(id),
      { initialProps: { id: 1 } },
    )

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockedFetch).toHaveBeenCalledWith({ robot_model_id: 1 })
    expect(result.current.scripts[0].sopId).toBe('SOP-001')

    rerender({ id: 2 })

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockedFetch).toHaveBeenCalledWith({ robot_model_id: 2 })
    expect(result.current.scripts[0].sopId).toBe('SOP-002')
    expect(mockedFetch).toHaveBeenCalledTimes(2)
  })
})
