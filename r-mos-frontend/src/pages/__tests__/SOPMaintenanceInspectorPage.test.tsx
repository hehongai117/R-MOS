import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  setOperationModeMock,
  setCurrentToolMock,
  preloadAllPartsMock,
  clientGetMock,
  clientPostMock,
  navigateMock,
  runDiagnosisActionMock,
} = vi.hoisted(() => ({
  setOperationModeMock: vi.fn(),
  setCurrentToolMock: vi.fn(),
  preloadAllPartsMock: vi.fn(),
  clientGetMock: vi.fn(),
  clientPostMock: vi.fn(),
  navigateMock: vi.fn(),
  runDiagnosisActionMock: vi.fn(),
}))

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)
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

Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', {
  configurable: true,
  value: vi.fn(),
})

Object.defineProperty(document, 'exitFullscreen', {
  configurable: true,
  value: vi.fn(),
})

vi.mock('@/api/client', () => ({
  default: {
    get: clientGetMock,
    post: clientPostMock,
    patch: vi.fn(),
  },
}))

vi.mock('@/api/agent-v2', () => ({
  runDiagnosisAction: runDiagnosisActionMock,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('@react-three/fiber', () => ({
  Canvas: () => <div>CanvasStub</div>,
}))

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => <div>OrbitControlsStub</div>,
}))

vi.mock('@/components/DiagnosisPanel/DiagnosisPanel', () => ({
  DiagnosisPanel: ({
    onConfirmExecution,
    onEscalateToTeacher,
  }: {
    onConfirmExecution: () => void
    onEscalateToTeacher: () => void
  }) => (
    <div>
      <div>DiagnosisPanelStub</div>
      <button type="button" onClick={onConfirmExecution}>
        确认执行方案
      </button>
      <button type="button" onClick={onEscalateToTeacher}>
        上报教师审核
      </button>
    </div>
  ),
  readLatestDiagnosisResult: () => ({
    diagnosisResult: null,
    maintenancePlan: null,
    verificationResult: null,
    traceId: 'trace-inspector-1',
  }),
}))

vi.mock('@/components/Viewer3D/Atom01Interactive', () => ({
  Atom01Interactive: () => <div>Atom01InteractiveStub</div>,
  PART_METADATA: {
    torso_link: {
      name: 'torso_link',
      displayName: '躯干',
      group: 'torso',
    },
  },
}))

vi.mock('@/components/Viewer3D/CameraController', () => ({
  CameraController: () => null,
}))

vi.mock('@/components/Viewer3D/DisassemblyDemoAdjudicated', () => ({
  default: () => <div>DisassemblyDemoStub</div>,
}))

vi.mock('@/components/Viewer3D/DisassemblyAnimation', () => ({
  DisassemblyAnimation: () => <div>DisassemblyAnimationStub</div>,
}))

vi.mock('@/components/Viewer3D/PartInspector', () => ({
  default: () => <div>PartInspectorStub</div>,
}))

vi.mock('@/components/Viewer3D/DetailParts', () => ({
  DetailParts: () => <div>DetailPartsStub</div>,
}))

vi.mock('@/components/Viewer3D/ModelPreloader', () => ({
  preloadAllParts: preloadAllPartsMock,
}))

vi.mock('@/components/Viewer3D/RuntimeAssetPreview', () => ({
  RuntimeAssetPreview: () => <div>RuntimeAssetPreviewStub</div>,
}))

vi.mock('@/components/Viewer3D/partsManifest', () => ({
  ALL_EXPLODE_PART_URLS: ['torso_link', 'left_arm_pitch_link'],
  ISOLATION_DENSITY_CONFIG: {
    N_fullscreen: 8,
    N_embed: 4,
    P_max: 6,
  },
  L0_OVERVIEW_PRESET: {
    position: [0, 0, 1],
    target: [0, 0, 0],
    fov: 45,
  },
  UI_CAPABILITIES: {
    allow_cross_jump: true,
  },
}))

vi.mock('@/components/Viewer3D/assemblyTree', () => ({
  getL1CameraPreset: () => ({ position: [0, 0, 1], target: [0, 0, 0], fov: 45 }),
  getL2CameraPreset: () => ({ position: [0, 0, 1], target: [0, 0, 0], fov: 45 }),
  getLinkDisplayName: (linkName: string) => linkName,
  getLinkDetailParts: () => [],
  linkHasDetailParts: () => false,
}))

vi.mock('@/components/Maintenance', async () => {
  const actual = await vi.importActual<typeof import('@/components/Maintenance')>('@/components/Maintenance')
  return {
    ...actual,
    ToolSelector: () => <div>ToolSelectorStub</div>,
    ScrewInfo: () => <div>ScrewInfoStub</div>,
  }
})

vi.mock('@/components/Maintenance/SOPPlayerAdjudicated', () => ({
  SOPPlayerAdjudicated: () => <div>SOPPlayerStub</div>,
}))

vi.mock('@/data/sopScripts', () => ({
  ALL_SOP_SCRIPTS: [
    {
      sopId: 'sop-1',
      title: '更换肘关节模组',
      difficulty: 'hard',
      steps: [
        {
          stepId: 'step-1',
          title: '拆卸外壳',
          description: '断电后拆除保护罩',
          onFailure: { action: 'block' },
          failureReasons: [{ severity: 'critical' }],
        },
      ],
    },
  ],
}))

vi.mock('@/data/maintenanceKnowledge', () => ({
  getCorePartDetailRecord: () => null,
  getDetailPartDetailRecord: () => null,
}))

vi.mock('@/adjudication', () => ({
  AdjudicationReport: class {},
  SOPExecutor: class {},
  SOPExecutionContext: class {},
  SOPScriptAdjudication: class {},
  SOPStepAdjudication: class {},
  SOPExecutionState: {
    IDLE: 'IDLE',
    PRECONDITION_CHECK: 'PRECONDITION_CHECK',
    EXECUTING: 'EXECUTING',
    VALIDATION: 'VALIDATION',
    COMPLETE: 'COMPLETE',
    FAILED: 'FAILED',
    BLOCKED: 'BLOCKED',
  },
  ErrorCategory: {
    INCOMPLETE_ACTION: 'incomplete',
  },
  useAdjudicationStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      operationMode: 'exam',
      setOperationMode: setOperationModeMock,
      setCurrentTool: setCurrentToolMock,
    }),
}))

vi.mock('@/adjudication/ui/useSOPSceneSync', () => ({
  useSOPSceneSync: () => ({
    state: {
      selectedSopId: 'sop-1',
      selectedSopTitle: '更换肘关节模组',
      currentStepTitle: '拆卸外壳',
      progressText: '1/1',
      executionState: 'EXECUTING',
      blockedReason: null,
    },
  }),
}))

vi.mock('@/adjudication/core/scoringEngine', () => ({
  scoringEngine: {
    getState: () => ({ currentScore: 96 }),
    subscribe: () => () => {},
    reset: vi.fn(),
  },
}))

vi.mock('@/adjudication/ui/examHeader', () => ({
  formatCountdown: () => '59:00',
  isCountdownUrgent: () => false,
}))

import SOPMaintenanceInspectorPage from '@/pages/SOPMaintenanceInspectorPage'

describe('SOPMaintenanceInspectorPage', () => {
  beforeEach(() => {
    setOperationModeMock.mockReset()
    setCurrentToolMock.mockReset()
    preloadAllPartsMock.mockReset()
    clientGetMock.mockReset()
    clientPostMock.mockReset()
    runDiagnosisActionMock.mockReset()
    clientGetMock.mockResolvedValue({ data: { projects: [] } })
    clientPostMock.mockResolvedValue({ data: {} })
  })

  it('renders inspection-focused layout with diagnosis and detail tabs', async () => {
    const user = userEvent.setup()

    render(<SOPMaintenanceInspectorPage />)

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
    expect(screen.getByRole('radiogroup', { name: '视图模式切换' })).toBeTruthy()
    expect(screen.getByRole('radio', { name: /正常/i })).toBeTruthy()
    expect(screen.getByRole('radio', { name: /爆炸图/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: '返回执行页' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '项目草案页' })).toBeTruthy()
    expect(screen.getByText('核心件快速定位')).toBeTruthy()
    expect(screen.getByText('DiagnosisPanelStub')).toBeTruthy()
    expect(screen.getByLabelText('SOP 3D 视图区')).toBeTruthy()
    expect(screen.queryByText('ToolSelectorStub')).toBeNull()
    expect(screen.queryByText('维保模式')).toBeNull()
    expect(screen.queryByText('零件总数')).toBeNull()
    expect(screen.queryByText('细节')).toBeNull()
    expect(screen.queryByText('教学模式')).toBeNull()
    expect(screen.queryByText('考试模式')).toBeNull()

    await user.click(screen.getByRole('tab', { name: '螺丝' }))

    await waitFor(() => {
      expect(screen.getByText('ScrewInfoStub')).toBeTruthy()
    })
  })

  it('submits confirm diagnosis action through backend api', async () => {
    runDiagnosisActionMock.mockResolvedValue({
      trace_id: 'trace-inspector-1',
      action: 'confirm_execution',
      message: '已确认执行方案，请转入 SOP 工作台执行。',
      recorded: true,
    })

    const user = userEvent.setup()

    render(<SOPMaintenanceInspectorPage />)

    await user.click(screen.getByRole('button', { name: '确认执行方案' }))

    await waitFor(() => {
      expect(runDiagnosisActionMock).toHaveBeenCalledWith('trace-inspector-1', 'confirm_execution')
    })
  })

  it('submits escalate diagnosis action through backend api', async () => {
    runDiagnosisActionMock.mockResolvedValue({
      trace_id: 'trace-inspector-1',
      action: 'escalate_to_teacher',
      message: '已上报教师审核，请等待处理。',
      recorded: true,
    })

    const user = userEvent.setup()

    render(<SOPMaintenanceInspectorPage />)

    await user.click(screen.getByRole('button', { name: '上报教师审核' }))

    await waitFor(() => {
      expect(runDiagnosisActionMock).toHaveBeenCalledWith('trace-inspector-1', 'escalate_to_teacher')
    })
  })
})
