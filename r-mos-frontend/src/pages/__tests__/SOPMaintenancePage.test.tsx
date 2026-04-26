import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  setOperationModeMock,
  setCurrentToolMock,
  preloadAllPartsMock,
  clientGetMock,
  clientPostMock,
  navigateMock,
} = vi.hoisted(() => ({
  setOperationModeMock: vi.fn(),
  setCurrentToolMock: vi.fn(),
  preloadAllPartsMock: vi.fn(),
  clientGetMock: vi.fn(),
  clientPostMock: vi.fn(),
  navigateMock: vi.fn(),
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

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  }
})

vi.mock('@react-three/fiber', () => ({
  Canvas: () => <div>CanvasStub</div>,
}))

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => <div>OrbitControlsStub</div>,
}))

vi.mock('@/components/DiagnosisPanel/DiagnosisPanel', () => ({
  DiagnosisPanel: () => <div>DiagnosisPanelStub</div>,
  readLatestDiagnosisResult: () => ({
    diagnosisResult: null,
    maintenancePlan: null,
    verificationResult: null,
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

import SOPMaintenancePage from '@/pages/SOPMaintenancePage'

describe('SOPMaintenancePage', () => {
  beforeEach(() => {
    setOperationModeMock.mockReset()
    setCurrentToolMock.mockReset()
    preloadAllPartsMock.mockReset()
    clientGetMock.mockReset()
    clientPostMock.mockReset()
    clientGetMock.mockResolvedValue({ data: { projects: [] } })
    clientPostMock.mockResolvedValue({ data: {} })
  })

  it('renders shell layout with collapsed sop list and without explode or hover helper panels', async () => {
    const user = userEvent.setup()

    render(<SOPMaintenancePage />)

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
    expect(screen.getByRole('radiogroup', { name: '视图模式切换' })).toBeTruthy()
    expect(screen.getByRole('radio', { name: /正常/i })).toBeTruthy()
    expect(screen.getByRole('radio', { name: /爆炸图/i })).toBeTruthy()
    expect(screen.queryByText('步骤导航、3D 操作区和工具要求统一在同一工作台内处理')).toBeNull()
    expect(screen.queryByText('执行页仅保留步骤、工具、播放器与 3D 操作区')).toBeNull()
    expect(screen.queryByText('分析信息已迁移到独立检视页，减少执行中断。')).toBeNull()
    expect(screen.queryByText('项目草案入口')).toBeNull()
    expect(screen.getByRole('button', { name: '项目草案页' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '打开检视页' })).toBeTruthy()
    expect(screen.getAllByText('更换肘关节模组').length).toBeGreaterThan(0)
    expect(screen.getByText('ToolSelectorStub')).toBeTruthy()
    expect(screen.getByLabelText('SOP 3D 视图区')).toBeTruthy()
    expect(screen.queryByText('ScrewInfoStub')).toBeFalsy()
    expect(screen.queryByText('核心件快速定位')).toBeNull()
    expect(screen.queryByText('DiagnosisPanelStub')).toBeNull()
    expect(screen.queryByText('爆炸图控制')).toBeNull()
    expect(screen.queryByText('当前悬停')).toBeNull()
    expect(screen.queryByRole('button', { name: '更换肘关节模组' })).toBeNull()
    expect(screen.getByRole('button', { name: '展开 SOP 列表' })).toBeTruthy()
    expect(screen.queryByText('维保模式')).toBeNull()
    expect(screen.queryByText('零件总数')).toBeNull()
    expect(screen.queryByText('细节')).toBeNull()
    expect(screen.queryByText('教学模式')).toBeNull()
    expect(screen.queryByText('考试模式')).toBeNull()

    await user.click(screen.getByRole('button', { name: '展开 SOP 列表' }))

    expect(screen.getByRole('button', { name: '收起 SOP 列表' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '更换肘关节模组' })).toBeTruthy()
  })

  it('keeps atom01 maintenance workbench as a dedicated full page without the project draft entry', () => {
    render(<SOPMaintenancePage workspaceVariant="atom01" />)

    expect(screen.getByRole('heading', { name: 'ATOM01 维保工作台' })).toBeTruthy()
    expect(screen.queryByText('步骤导航、3D 操作区和工具要求统一在同一工作台内处理')).toBeNull()
    expect(screen.queryByText('项目草案入口')).toBeNull()
    expect(screen.queryByRole('button', { name: '进入项目草案页' })).toBeNull()
    expect(screen.getByLabelText('SOP 3D 视图区')).toBeTruthy()
  })
})
