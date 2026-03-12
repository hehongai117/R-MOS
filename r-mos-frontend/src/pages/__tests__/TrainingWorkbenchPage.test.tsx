import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  generateTrainingWorkbenchDraftMock,
  getActiveTrainingSessionMock,
  getTrainingSessionDetailMock,
  navigateMock,
  useAuthStoreMock,
} = vi.hoisted(() => ({
  generateTrainingWorkbenchDraftMock: vi.fn(),
  getActiveTrainingSessionMock: vi.fn(),
  getTrainingSessionDetailMock: vi.fn(),
  navigateMock: vi.fn(),
  useAuthStoreMock: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('@/api/training', () => ({
  getActiveTrainingSession: getActiveTrainingSessionMock,
  getTrainingSessionDetail: getTrainingSessionDetailMock,
  generateTrainingWorkbenchDraft: generateTrainingWorkbenchDraftMock,
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: useAuthStoreMock,
}))

vi.mock('@/components/Viewer3D', () => ({
  Atom01Viewer: () => <div data-testid="atom01-viewer" />,
}))

import TrainingWorkbenchPage from '@/pages/TrainingWorkbenchPage'
import { workbenchStore } from '@/store/workbenchStore'

describe('TrainingWorkbenchPage', () => {
  beforeEach(() => {
    workbenchStore.getState().resetTrainingProject()
    getActiveTrainingSessionMock.mockReset()
    getTrainingSessionDetailMock.mockReset()
    generateTrainingWorkbenchDraftMock.mockReset()
    navigateMock.mockReset()
    useAuthStoreMock.mockImplementation((selector: (state: Record<string, unknown>) => unknown) =>
      selector({
        user: {
          user_id: 7,
          email: 'student@rmos.test',
          full_name: 'Student User',
          role: 'student',
        },
      }),
    )
    getActiveTrainingSessionMock.mockRejectedValue(new Error('No active session found'))
  })

  it('renders ai draft generator when no active session exists', async () => {
    render(<TrainingWorkbenchPage />)

    expect(await screen.findByText('AI 生成训练草案')).toBeTruthy()
    expect(screen.getByLabelText('机器人型号')).toBeTruthy()
    expect(screen.getByLabelText('训练任务')).toBeTruthy()
    expect(screen.getByRole('button', { name: '生成训练草案' })).toBeTruthy()
  })

  it('hydrates the workbench with ai generated draft', async () => {
    generateTrainingWorkbenchDraftMock.mockResolvedValue({
      project: {
        sessionId: 'draft-session',
        projectId: 'draft-project',
        title: 'ATOM01 关节盖拆装训练',
        progressPercent: 0,
      },
      steps: [
        {
          id: 'draft-step-1',
          title: '步骤 1: 准备工位',
          status: 'active',
          instruction: '确认断电挂牌与 PPE。',
          evidenceHint: '上传工位照片。',
          tools: [
            { id: 'tool-glove', name: '绝缘手套', spec: 'A级绝缘', isCritical: true },
          ],
        },
      ],
      messages: [
        {
          id: 'msg-1',
          role: 'assistant',
          content: '先确认绝缘手套和断电挂牌。',
          createdAt: '2026-03-12T10:00:00.000Z',
        },
      ],
    })

    const user = userEvent.setup()
    render(<TrainingWorkbenchPage />)

    await screen.findByText('AI 生成训练草案')
    await user.clear(screen.getByLabelText('训练任务'))
    await user.type(screen.getByLabelText('训练任务'), '髋关节电机盖拆装')
    await user.click(screen.getByRole('button', { name: '生成训练草案' }))

    await waitFor(() => {
      expect(generateTrainingWorkbenchDraftMock).toHaveBeenCalledWith({
        robotModel: 'ATOM01',
        taskSummary: '髋关节电机盖拆装',
        focusPrompt: '强调工具确认、证据留存与 AI 提示',
      })
    })

    expect((await screen.findAllByText('步骤 1: 准备工位')).length).toBeGreaterThan(0)
    expect(screen.getByText('绝缘手套')).toBeTruthy()
    expect(screen.getByText('先确认绝缘手套和断电挂牌。')).toBeTruthy()
    expect(screen.getByText('上传工位照片。')).toBeTruthy()
  })
})
