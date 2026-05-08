import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../client'
import {
  createRobot,
  deleteRobot,
  getRobot,
  listAnalysisTasks,
  listRobots,
  togglePublish,
  toggleVisibility,
  triggerAnalysis,
  updateRobot,
  uploadRobotFiles,
} from '../robots'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
const mockPut = vi.mocked(apiClient.put)
const mockDelete = vi.mocked(apiClient.delete)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('robots API', () => {
  it('listRobots calls GET /robots', async () => {
    const data = { items: [], total: 0 }
    mockGet.mockResolvedValue({ data })
    const result = await listRobots()
    expect(mockGet).toHaveBeenCalledWith('/robots')
    expect(result).toEqual(data)
  })

  it('createRobot calls POST /robots', async () => {
    const robot = { id: 1, brand: 'Test' }
    mockPost.mockResolvedValue({ data: robot })
    const result = await createRobot({ brand: 'Test', model_name: 'T1' })
    expect(mockPost).toHaveBeenCalledWith('/robots', { brand: 'Test', model_name: 'T1' })
    expect(result).toEqual(robot)
  })

  it('getRobot calls GET /robots/:id', async () => {
    const robot = { id: 5 }
    mockGet.mockResolvedValue({ data: robot })
    const result = await getRobot(5)
    expect(mockGet).toHaveBeenCalledWith('/robots/5')
    expect(result).toEqual(robot)
  })

  it('updateRobot calls PUT /robots/:id', async () => {
    const robot = { id: 5, brand: 'Updated' }
    mockPut.mockResolvedValue({ data: robot })
    const result = await updateRobot(5, { brand: 'Updated' })
    expect(mockPut).toHaveBeenCalledWith('/robots/5', { brand: 'Updated' })
    expect(result).toEqual(robot)
  })

  it('deleteRobot calls DELETE /robots/:id', async () => {
    mockDelete.mockResolvedValue({ data: undefined })
    await deleteRobot(5)
    expect(mockDelete).toHaveBeenCalledWith('/robots/5')
  })

  it('uploadRobotFiles sends FormData to POST /robots/:id/upload', async () => {
    const uploaded = { uploaded: [], failed: [] }
    mockPost.mockResolvedValue({ data: uploaded })
    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    const result = await uploadRobotFiles(5, [file])
    expect(mockPost).toHaveBeenCalledWith(
      '/robots/5/upload',
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } }),
    )
    expect(result).toEqual(uploaded)
  })

  it('triggerAnalysis calls POST /robots/:id/analyze', async () => {
    const task = { id: 1, status: 'pending' }
    mockPost.mockResolvedValue({ data: task })
    const result = await triggerAnalysis(5)
    expect(mockPost).toHaveBeenCalledWith('/robots/5/analyze')
    expect(result).toEqual(task)
  })

  it('listAnalysisTasks calls GET /robots/:id/analysis-tasks', async () => {
    const data = { items: [], total: 0 }
    mockGet.mockResolvedValue({ data })
    const result = await listAnalysisTasks(5)
    expect(mockGet).toHaveBeenCalledWith('/robots/5/analysis-tasks')
    expect(result).toEqual(data)
  })

  it('togglePublish calls PUT /robots/:id/publish', async () => {
    const robot = { id: 5, status: 'ready' }
    mockPut.mockResolvedValue({ data: robot })
    const result = await togglePublish(5)
    expect(mockPut).toHaveBeenCalledWith('/robots/5/publish')
    expect(result).toEqual(robot)
  })

  it('toggleVisibility calls PUT /robots/:id/visibility', async () => {
    const robot = { id: 5, visibility: 'shared' }
    mockPut.mockResolvedValue({ data: robot })
    const result = await toggleVisibility(5)
    expect(mockPut).toHaveBeenCalledWith('/robots/5/visibility')
    expect(result).toEqual(robot)
  })
})
