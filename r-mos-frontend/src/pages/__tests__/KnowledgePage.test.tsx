import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  searchKnowledgeMock,
  createKnowledgeMock,
  submitKnowledgeForReviewMock,
  approveKnowledgeMock,
  uploadKnowledgeFileMock,
  getKnowledgeUploadJobMock,
  clientGetMock,
  teacherState,
  studentState,
} = vi.hoisted(() => ({
  searchKnowledgeMock: vi.fn(),
  createKnowledgeMock: vi.fn(),
  submitKnowledgeForReviewMock: vi.fn(),
  approveKnowledgeMock: vi.fn(),
  uploadKnowledgeFileMock: vi.fn(),
  getKnowledgeUploadJobMock: vi.fn(),
  clientGetMock: vi.fn(),
  teacherState: {
    user: {
      role: 'teacher',
      email: 'teacher1@rmos.test',
    },
  },
  studentState: {
    user: {
      role: 'student',
      email: 'student_a@rmos.test',
    },
  },
}))

let authState = teacherState

vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}))

Object.defineProperty(window, 'getComputedStyle', {
  configurable: true,
  value: () => ({
    getPropertyValue: () => '',
  }),
})

vi.mock('@/store/authStore', () => ({
  useAuthStore: (selector: (state: typeof teacherState) => unknown) => selector(authState),
}))

vi.mock('@/api/client', () => ({
  default: {
    get: clientGetMock,
    post: vi.fn(),
    patch: vi.fn(),
  },
}))

vi.mock('@/api/agent', () => ({
  searchKnowledge: searchKnowledgeMock,
  createKnowledge: createKnowledgeMock,
  submitKnowledgeForReview: submitKnowledgeForReviewMock,
  approveKnowledge: approveKnowledgeMock,
  uploadKnowledgeFile: uploadKnowledgeFileMock,
  getKnowledgeUploadJob: getKnowledgeUploadJobMock,
}))

import KnowledgePage from '@/pages/KnowledgePage'

describe('KnowledgePage', () => {
  beforeEach(() => {
    authState = teacherState
    searchKnowledgeMock.mockReset()
    createKnowledgeMock.mockReset()
    submitKnowledgeForReviewMock.mockReset()
    approveKnowledgeMock.mockReset()
    uploadKnowledgeFileMock.mockReset()
    getKnowledgeUploadJobMock.mockReset()
    clientGetMock.mockReset()

    searchKnowledgeMock.mockResolvedValue({ results: [] })
    clientGetMock.mockResolvedValue({
      data: {
        projects: [
          {
            project_id: 'project-fourier-n1',
            robot_key: 'fourier-n1-runtime',
            brand: 'Fourier',
            model: 'N1',
            version: 'runtime',
            status: 'ready',
            ingest_summary: {
              files_total: 6,
              chunks_total: 5,
            },
          },
        ],
      },
    })
  })

  it('shows a robot project ingest workspace for teacher users while preserving legacy search', async () => {
    render(<KnowledgePage />)

    expect(screen.getByRole('heading', { name: '知识库' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: '知识搜索' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: '机器人项目' })).toBeTruthy()

    await userEvent.click(screen.getByRole('tab', { name: '机器人项目' }))

    await waitFor(() => {
      expect(screen.getByText('机器人项目包上传')).toBeTruthy()
    })

    expect(screen.getByLabelText('机器人品牌')).toBeTruthy()
    expect(screen.getByLabelText('机器人型号')).toBeTruthy()
    expect(screen.getByLabelText('版本标识')).toBeTruthy()
    expect(screen.getByText('最近项目')).toBeTruthy()
    expect(screen.getByText('Fourier')).toBeTruthy()
    expect(screen.getByText('N1')).toBeTruthy()
  })

  it('hides ingest controls for students and keeps robot project browsing available', async () => {
    authState = studentState

    render(<KnowledgePage />)

    expect(screen.queryByRole('tab', { name: '创建知识' })).toBeFalsy()
    expect(screen.getByRole('tab', { name: '机器人项目' })).toBeTruthy()

    await userEvent.click(screen.getByRole('tab', { name: '机器人项目' }))

    await waitFor(() => {
      expect(screen.getByText('最近项目')).toBeTruthy()
    })

    expect(screen.queryByText('机器人项目包上传')).toBeFalsy()
    expect(screen.getByText('Fourier')).toBeTruthy()
  })
})
