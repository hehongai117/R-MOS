import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)

const {
  generateTrainingWorkbenchDraftMock,
  getActiveTrainingSessionMock,
  getTrainingSessionDetailMock,
  uploadTrainingWorkbenchEvidenceMock,
  submitTrainingWorkbenchStepMock,
  askTrainingWorkbenchAssistantMock,
  navigateMock,
  useAuthStoreMock,
} = vi.hoisted(() => ({
  generateTrainingWorkbenchDraftMock: vi.fn(),
  getActiveTrainingSessionMock: vi.fn(),
  getTrainingSessionDetailMock: vi.fn(),
  uploadTrainingWorkbenchEvidenceMock: vi.fn(),
  submitTrainingWorkbenchStepMock: vi.fn(),
  askTrainingWorkbenchAssistantMock: vi.fn(),
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
  uploadTrainingWorkbenchEvidence: uploadTrainingWorkbenchEvidenceMock,
  submitTrainingWorkbenchStep: submitTrainingWorkbenchStepMock,
  askTrainingWorkbenchAssistant: askTrainingWorkbenchAssistantMock,
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: useAuthStoreMock,
}))

vi.mock('@/components/Viewer3D', () => ({
  Atom01Viewer: ({ highlightLinks }: { highlightLinks?: string[] }) => (
    <div data-highlight={highlightLinks?.join(',') ?? ''} data-testid="atom01-viewer" />
  ),
}))

import TrainingWorkbenchPage from '@/pages/TrainingWorkbenchPage'
import { workbenchStore } from '@/store/workbenchStore'

describe('TrainingWorkbenchPage', () => {
  beforeEach(() => {
    workbenchStore.getState().resetTrainingProject()
    getActiveTrainingSessionMock.mockReset()
    getTrainingSessionDetailMock.mockReset()
    generateTrainingWorkbenchDraftMock.mockReset()
    uploadTrainingWorkbenchEvidenceMock.mockReset()
    submitTrainingWorkbenchStepMock.mockReset()
    askTrainingWorkbenchAssistantMock.mockReset()
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
          stepIndex: 0,
          title: '步骤 1: 准备工位',
          status: 'active',
          instruction: '确认断电挂牌与 PPE。',
          evidenceHint: '上传工位照片。',
          modelTargets: ['torso_link'],
          tools: [
            { id: 'tool-glove', name: '绝缘手套', spec: 'A级绝缘', isCritical: true },
            { id: 'tool-wrench', name: '扭矩扳手', spec: '5-25Nm', isCritical: true },
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
    expect(screen.getByTestId('atom01-viewer').getAttribute('data-highlight')).toBe('torso_link')
  })

  it('uploads evidence, submits current step and asks the assistant', async () => {
    generateTrainingWorkbenchDraftMock.mockResolvedValue({
      project: {
        sessionId: 'session-1',
        projectId: 'draft-project',
        title: 'ATOM01 关节盖拆装训练',
        progressPercent: 0,
      },
      steps: [
        {
          id: 'draft-step-1',
          stepIndex: 0,
          title: '步骤 1: 准备工位',
          status: 'active',
          instruction: '确认断电挂牌与 PPE。',
          evidenceHint: '上传工位照片。',
          modelTargets: ['torso_link'],
          tools: [
            { id: 'tool-glove', name: '绝缘手套', spec: 'A级绝缘', isCritical: true },
            { id: 'tool-wrench', name: '扭矩扳手', spec: '5-25Nm', isCritical: true },
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
    uploadTrainingWorkbenchEvidenceMock.mockResolvedValue({
      evidenceBundleId: 'bundle-1',
      filename: 'station.jpg',
      contentUri: 'local://training-evidence/session-1/station.jpg',
    })
    submitTrainingWorkbenchStepMock.mockResolvedValue({
      recordId: 'record-1',
      status: 'pass',
      evidenceBundleId: 'bundle-1',
      nextStepId: null,
      sessionSubmitted: false,
      verdict: {
        result: 'PASS',
        summary: '已满足提交条件',
        details: '关键工具已确认，证据已入库。',
      },
    })
    askTrainingWorkbenchAssistantMock.mockResolvedValue({
      id: 'assistant-2',
      role: 'assistant',
      content: '建议先复核扭矩扳手量程。',
      createdAt: '2026-03-12T10:01:00.000Z',
    })

    const user = userEvent.setup()
    const { container } = render(<TrainingWorkbenchPage />)

    await screen.findByText('AI 生成训练草案')
    await user.click(screen.getByRole('button', { name: '生成训练草案' }))
    expect((await screen.findAllByText('步骤 1: 准备工位')).length).toBeGreaterThan(0)

    const fileInput = container.querySelector('input[type="file"]')
    expect(fileInput).toBeTruthy()
    await user.upload(fileInput as HTMLInputElement, new File(['evidence'], 'station.jpg', { type: 'image/jpeg' }))

    await user.click(screen.getByRole('button', { name: '将绝缘手套标记为已确认' }))
    await user.click(screen.getByRole('button', { name: '将扭矩扳手标记为已确认' }))
    await user.type(screen.getByPlaceholderText('记录当前步骤执行说明或异常备注'), '工位与 PPE 已核查。')
    await user.click(screen.getByRole('button', { name: '提交当前步骤' }))

    await waitFor(() => {
      expect(uploadTrainingWorkbenchEvidenceMock).toHaveBeenCalled()
      expect(submitTrainingWorkbenchStepMock).toHaveBeenCalledWith('session-1', 'draft-step-1', {
        stepIndex: 0,
        note: '工位与 PPE 已核查。',
        evidenceBundleId: 'bundle-1',
        toolsConfirmed: [
          { toolId: 'tool-glove', status: 'CONFIRMED' },
          { toolId: 'tool-wrench', status: 'CONFIRMED' },
        ],
      })
    })

    expect(screen.getByText('已满足提交条件')).toBeTruthy()

    await user.type(screen.getByPlaceholderText('向 AI 助手补充现场说明'), '扭矩扳手读数波动怎么办？')
    await user.click(screen.getByRole('button', { name: '发送给 AI 助手' }))

    await waitFor(() => {
      expect(askTrainingWorkbenchAssistantMock).toHaveBeenCalledWith({
        sessionId: 'session-1',
        stepId: 'draft-step-1',
        question: '扭矩扳手读数波动怎么办？',
        messages: expect.any(Array),
      })
    })

    expect(screen.getByText('建议先复核扭矩扳手量程。')).toBeTruthy()
  })
})
