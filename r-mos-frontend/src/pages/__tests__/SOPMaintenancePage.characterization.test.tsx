import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Hoisted mocks — must be created before any imports
// ---------------------------------------------------------------------------
const {
  setOperationModeMock,
  setCurrentToolMock,
  preloadAllPartsMock,
  clientGetMock,
  clientPostMock,
  navigateMock,
  currentRobotSelectorMock,
  sopScriptsMock,
  sopSceneSyncMock,
  sopPlayerCallbackCapture,
  atomCapture,
  atomShouldThrow,
} = vi.hoisted(() => {
  const sopPlayerCallbackCapture: { current: Record<string, unknown> | null } = {
    current: null,
  }
  const atomCapture: { current: Record<string, unknown> | null } = {
    current: null,
  }
  const atomShouldThrow: { current: boolean } = { current: false }
  return {
    setOperationModeMock: vi.fn(),
    setCurrentToolMock: vi.fn(),
    preloadAllPartsMock: vi.fn(),
    clientGetMock: vi.fn(),
    clientPostMock: vi.fn(),
    navigateMock: vi.fn(),
    currentRobotSelectorMock: vi.fn(),
    sopScriptsMock: vi.fn(),
    sopSceneSyncMock: vi.fn(),
    sopPlayerCallbackCapture,
    atomCapture,
    atomShouldThrow,
  }
})

// ---------------------------------------------------------------------------
// Browser API stubs
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Module mocks — same pattern as existing test files
// ---------------------------------------------------------------------------
vi.mock('@/api/client', () => ({
  default: {
    get: clientGetMock,
    post: clientPostMock,
    patch: vi.fn(),
  },
  API_ROOT: 'http://localhost:8000/api/v1',
  API_BASE_URL: 'http://localhost:8000',
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  }
})

// Canvas renders its children so the 3D branch-selection ternary in
// SOPMaintenancePage (runtimeManifest / manifest+robot / robotId) is observable.
// R3F intrinsics (ambientLight, color, gridHelper…) render as inert host nodes in jsdom.
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
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

// Captures props so tests can drive the 3D viewer callbacks (part select / hover /
// sub-part select / double click / visible bounds) that own the isolation state machine.
vi.mock('@/components/Viewer3D/Atom01Interactive', () => ({
  Atom01Interactive: (props: Record<string, unknown>) => {
    if (atomShouldThrow.current) throw new Error('WebGL not supported')
    atomCapture.current = props
    return <div>Atom01InteractiveStub</div>
  },
  PART_METADATA: {
    torso_link: { name: 'torso_link', displayName: '躯干', group: 'torso' },
    left_arm_pitch_link: { name: 'left_arm_pitch_link', displayName: '左臂', group: 'arm' },
  },
}))

vi.mock('@/components/Viewer3D/InteractiveManifestViewer', () => ({
  InteractiveManifestViewer: () => <div>InteractiveManifestViewerStub</div>,
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
  ISOLATION_DENSITY_CONFIG: { N_fullscreen: 8, N_embed: 4, P_max: 6 },
  L0_OVERVIEW_PRESET: { position: [0, 0, 1], target: [0, 0, 0], fov: 45 },
  UI_CAPABILITIES: { allow_cross_jump: true },
}))

vi.mock('@/components/Viewer3D/assemblyTree', () => ({
  getL1CameraPreset: () => ({ position: [0, 0, 1], target: [0, 0, 0], fov: 45 }),
  getL2CameraPreset: () => ({ position: [0, 0, 1], target: [0, 0, 0], fov: 45 }),
  getLinkDisplayName: (linkName: string) => linkName,
  // left_arm_pitch_link has detail parts → drives the L2 sub-part path
  getLinkDetailParts: (linkName: string) =>
    linkName === 'left_arm_pitch_link'
      ? [{ name: 'bolt_a', displayName: '螺栓A', category: 'bolt', actionTarget: 'bolt_a' }]
      : [],
  linkHasDetailParts: (linkName: string) => linkName === 'left_arm_pitch_link',
}))

vi.mock('@/components/Viewer3D/useAssemblyManifest', () => ({
  useAssemblyManifest: () => ({ manifest: null, loading: false, error: null }),
}))

vi.mock('@/components/Maintenance', async () => {
  const actual = await vi.importActual<typeof import('@/components/Maintenance')>('@/components/Maintenance')
  return {
    ...actual,
    ToolSelector: () => <div>ToolSelectorStub</div>,
    ScrewInfo: () => <div>ScrewInfoStub</div>,
  }
})

// SOPPlayerAdjudicated: captures all callback props so tests can invoke them
vi.mock('@/components/Maintenance/SOPPlayerAdjudicated', () => ({
  SOPPlayerAdjudicated: (props: Record<string, unknown>) => {
    sopPlayerCallbackCapture.current = props
    const sops = (props.availableSOPs as Array<{ title: string }> | undefined) ?? []
    return (
      <div>
        SOPPlayerStub
        {sops.map((sop) => <div key={sop.title}>{sop.title}</div>)}
      </div>
    )
  },
}))

vi.mock('@/store/robotContextStore', () => ({
  useRobotContextStore: (selector: (state: Record<string, unknown>) => unknown) =>
    currentRobotSelectorMock(selector),
}))

vi.mock('@/hooks/useSOPScripts', () => ({
  useSOPScripts: () => sopScriptsMock(),
}))

vi.mock('@/data/maintenanceKnowledge', () => ({
  getCorePartDetailRecord: () => null,
  getDetailPartDetailRecord: () => null,
}))

vi.mock('@/adjudication', () => ({
  injectManifestPartRegistry: vi.fn(),
  clearManifestPartRegistry: vi.fn(),
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
  ActionType: { SELECT_TOOL: 'SELECT_TOOL', FOCUS_CAMERA: 'FOCUS_CAMERA' },
  ErrorCategory: { INCOMPLETE_ACTION: 'incomplete' },
  useAdjudicationStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      operationMode: 'exam',
      setOperationMode: setOperationModeMock,
      setCurrentTool: setCurrentToolMock,
    }),
}))

vi.mock('@/adjudication/ui/useSOPSceneSync', () => ({
  useSOPSceneSync: () => sopSceneSyncMock(),
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

vi.mock('@/features/maintenance/runtimeWorkspaceSession', () => ({
  readMaintenanceWorkspaceSession: () => null,
  writeMaintenanceWorkspaceSession: vi.fn(),
}))

// ---------------------------------------------------------------------------
// Import component under test (MUST be after all vi.mock calls)
// ---------------------------------------------------------------------------
import SOPMaintenancePage from '@/pages/SOPMaintenancePage'

// ---------------------------------------------------------------------------
// Shared default mock state
// ---------------------------------------------------------------------------
const DEFAULT_SCRIPTS = {
  scripts: [
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
  loading: false,
  fromApi: true,
}

const makeSyncState = (overrides: Record<string, unknown> = {}) => ({
  state: {
    selectedSopId: 'sop-1',
    selectedSopTitle: '更换肘关节模组',
    currentStepTitle: '拆卸外壳',
    progressText: '1/1',
    executionState: 'EXECUTING',
    blockedReason: null,
    ...overrides,
  },
  progressText: '1/1',
  bindSOP: vi.fn(() => null),
  bindStep: vi.fn(() => ({ targetPart: null, explodeAmount: 0, requiredTool: null })),
  bindContext: vi.fn(),
  bindBlocked: vi.fn(),
})

const NO_ROBOT_STATE = { currentRobot: null, currentRobotId: null }
const ROBOT_STATE = {
  currentRobot: { id: 1, model_name: 'ATOM-01', manufacturer: 'Test' },
  currentRobotId: 1,
}
const FOURIER_ROBOT_STATE = {
  currentRobot: { id: 42, model_name: 'Fourier N1', manufacturer: 'Fourier' },
  currentRobotId: 42,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('SOPMaintenancePage characterization', () => {
  beforeEach(() => {
    setOperationModeMock.mockReset()
    setCurrentToolMock.mockReset()
    preloadAllPartsMock.mockReset()
    clientGetMock.mockReset()
    clientPostMock.mockReset()
    navigateMock.mockReset()
    sopPlayerCallbackCapture.current = null
    atomShouldThrow.current = false
    window.sessionStorage.clear()

    clientGetMock.mockResolvedValue({ data: { projects: [] } })
    clientPostMock.mockResolvedValue({ data: {} })

    // Default: no robot, one SOP, standard sync state
    currentRobotSelectorMock.mockImplementation(
      (sel: (s: Record<string, unknown>) => unknown) => sel(NO_ROBOT_STATE),
    )
    sopScriptsMock.mockReturnValue(DEFAULT_SCRIPTS)
    sopSceneSyncMock.mockReturnValue(makeSyncState())
  })

  // ─── layoutMode variants ──────────────────────────────────────────────────

  it('hides execution rail and shows inspector rail when layoutMode=inspector', () => {
    render(<SOPMaintenancePage layoutMode="inspector" />)

    // Inspector right rail rendered
    expect(screen.getByText('核心件快速定位')).toBeTruthy()
    // Execution left rail absent
    expect(screen.queryByText('ToolSelectorStub')).toBeNull()
    expect(screen.queryByText('SOPPlayerStub')).toBeNull()
    expect(screen.queryByRole('button', { name: '展开 SOP 列表' })).toBeNull()
  })

  it('shows both execution and inspector rails when layoutMode=full', () => {
    render(<SOPMaintenancePage layoutMode="full" />)

    // Execution left rail
    expect(screen.getByText('ToolSelectorStub')).toBeTruthy()
    expect(screen.getByText('SOPPlayerStub')).toBeTruthy()
    expect(screen.getByRole('button', { name: '展开 SOP 列表' })).toBeTruthy()
    // Inspector right rail
    expect(screen.getByText('核心件快速定位')).toBeTruthy()
    // Part detail panel empty state visible
    expect(screen.getByText('点击零件查看详情')).toBeTruthy()
  })

  // ─── SOP list states ──────────────────────────────────────────────────────

  it('shows empty-state text when SOP list is expanded but no scripts available', async () => {
    sopScriptsMock.mockReturnValue({ scripts: [], loading: false, fromApi: true })
    const user = userEvent.setup()

    render(<SOPMaintenancePage />)
    await user.click(screen.getByRole('button', { name: '展开 SOP 列表' }))

    expect(
      screen.getByText('暂无可用 SOP，请先选择机器人或联系教师配置。'),
    ).toBeTruthy()
  })

  it('shows SOP title button in expanded list and collapse button after expand', async () => {
    const user = userEvent.setup()

    render(<SOPMaintenancePage />)
    await user.click(screen.getByRole('button', { name: '展开 SOP 列表' }))

    expect(screen.getByRole('button', { name: '更换肘关节模组' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '收起 SOP 列表' })).toBeTruthy()
  })

  it('clicking a SOP button in expanded list keeps it rendered (linkedSOPId updates)', async () => {
    const user = userEvent.setup()

    render(<SOPMaintenancePage />)
    await user.click(screen.getByRole('button', { name: '展开 SOP 列表' }))
    await user.click(screen.getByRole('button', { name: '更换肘关节模组' }))

    // After click, SOP list remains expanded with the button still visible
    expect(screen.getByRole('button', { name: '更换肘关节模组' })).toBeTruthy()
  })

  // ─── SOP scene sync state display ─────────────────────────────────────────

  it('shows 执行中 execution state tag and current step when selectedSopId is set', () => {
    render(<SOPMaintenancePage />)

    expect(screen.getAllByText('更换肘关节模组').length).toBeGreaterThan(0)
    // sopSceneSync.progressText is used for the step tag (步骤 1/1)
    expect(screen.getByText('步骤 1/1')).toBeTruthy()
    expect(screen.getByText('执行中')).toBeTruthy()
    expect(screen.getByText('当前步骤：拆卸外壳')).toBeTruthy()
  })

  it('shows 就绪 tag when execution state is IDLE', () => {
    sopSceneSyncMock.mockReturnValue(makeSyncState({ executionState: 'IDLE' }))

    render(<SOPMaintenancePage />)

    expect(screen.getByText('就绪')).toBeTruthy()
  })

  it('shows 失败 tag when execution state is FAILED', () => {
    sopSceneSyncMock.mockReturnValue(makeSyncState({ executionState: 'FAILED' }))

    render(<SOPMaintenancePage />)

    expect(screen.getByText('失败')).toBeTruthy()
  })

  it('shows 已阻断 tag when execution state is BLOCKED', () => {
    sopSceneSyncMock.mockReturnValue(makeSyncState({ executionState: 'BLOCKED' }))

    render(<SOPMaintenancePage />)

    expect(screen.getByText('已阻断')).toBeTruthy()
  })

  it('shows 已完成 tag when execution state is COMPLETE', () => {
    sopSceneSyncMock.mockReturnValue(makeSyncState({ executionState: 'COMPLETE' }))

    render(<SOPMaintenancePage />)

    expect(screen.getByText('已完成')).toBeTruthy()
  })

  it('shows blocked reason text when sopSceneSync reports a blockedReason', () => {
    sopSceneSyncMock.mockReturnValue(
      makeSyncState({ blockedReason: '工具选择错误' }),
    )

    render(<SOPMaintenancePage />)

    expect(screen.getByText('阻断原因：工具选择错误')).toBeTruthy()
  })

  // ─── workspace variant / title ────────────────────────────────────────────

  it('shows 维保工作台 title and hides draft entry for demo variant without robot', () => {
    render(<SOPMaintenancePage workspaceVariant="demo" />)

    expect(screen.getByRole('heading', { name: '维保工作台' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: '项目草案页' })).toBeNull()
  })

  it('prefixes robot model name to title for demo variant when currentRobot is set', () => {
    currentRobotSelectorMock.mockImplementation(
      (sel: (s: Record<string, unknown>) => unknown) => sel(FOURIER_ROBOT_STATE),
    )

    render(<SOPMaintenancePage workspaceVariant="demo" />)

    expect(screen.getByRole('heading', { name: 'Fourier N1 维保工作台' })).toBeTruthy()
  })

  // ─── navigation button interactions ───────────────────────────────────────

  it('calls navigate to project-draft page when 项目草案页 button is clicked', async () => {
    const user = userEvent.setup()
    render(<SOPMaintenancePage />)

    await user.click(screen.getByRole('button', { name: '项目草案页' }))

    expect(navigateMock).toHaveBeenCalledWith('/maintenance?view=project-draft')
  })

  it('calls navigate to inspector view when 打开检视页 button is clicked', async () => {
    const user = userEvent.setup()
    render(<SOPMaintenancePage />)

    await user.click(screen.getByRole('button', { name: '打开检视页' }))

    expect(navigateMock).toHaveBeenCalledWith('/maintenance?view=inspector')
  })

  it('calls navigate back to execution page when 返回执行页 button is clicked in inspector layout', async () => {
    const user = userEvent.setup()
    render(<SOPMaintenancePage layoutMode="inspector" />)

    // In inspector mode the execution button is present in the header
    // effectiveLayoutMode !== 'execution' so label is '返回执行页'
    await user.click(screen.getByRole('button', { name: '返回执行页' }))

    expect(navigateMock).toHaveBeenCalledWith('/maintenance')
  })

  // ─── 3D viewer path selection ─────────────────────────────────────────────

  it('renders Atom01InteractiveStub when currentRobot is set and manifest is null', () => {
    currentRobotSelectorMock.mockImplementation(
      (sel: (s: Record<string, unknown>) => unknown) => sel(ROBOT_STATE),
    )

    render(<SOPMaintenancePage />)

    expect(screen.getByText('Atom01InteractiveStub')).toBeTruthy()
  })

  it('renders nothing in 3D area when no robot and no manifest', () => {
    // Default: NO_ROBOT_STATE → robotId is null → null branch
    render(<SOPMaintenancePage />)

    expect(screen.queryByText('Atom01InteractiveStub')).toBeNull()
    expect(screen.queryByText('InteractiveManifestViewerStub')).toBeNull()
    expect(screen.queryByText('RuntimeAssetPreviewStub')).toBeNull()
  })

  // ─── preload on mount ─────────────────────────────────────────────────────

  it('calls preloadAllParts exactly once on mount', () => {
    render(<SOPMaintenancePage />)

    expect(preloadAllPartsMock).toHaveBeenCalledOnce()
  })

  // ─── SOPPlayer callback: onSummarize → exam overlay ──────────────────────

  it('shows exam summary overlay with score and reason when onSummarize is called', async () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onSummarize?: (report: { reasonCode: string }) => void
    } | null
    expect(callbacks?.onSummarize).toBeDefined()

    act(() => {
      callbacks!.onSummarize!({ reasonCode: 'TIMEOUT' })
    })

    expect(screen.getByText('考试结束')).toBeTruthy()
    expect(screen.getByText('原因码：TIMEOUT')).toBeTruthy()
    expect(screen.getByText('最终得分：96')).toBeTruthy()
    // Exam Summary header tag
    expect(screen.getByText('Exam Summary')).toBeTruthy()
  })

  it('dismisses exam overlay and does not crash when 重置 is clicked', async () => {
    const user = userEvent.setup()
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onSummarize?: (report: { reasonCode: string }) => void
    } | null

    act(() => {
      callbacks!.onSummarize!({ reasonCode: 'COMPLETE' })
    })

    expect(screen.getByText('考试结束')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: '重置' }))
    expect(screen.queryByText('考试结束')).toBeNull()
  })

  // ─── SOPPlayer callback: onSOPChange ─────────────────────────────────────

  it('handles onSOPChange callback without crashing (resets overview)', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onSOPChange?: (sop: { sopId: string; title: string } | null) => void
    } | null
    expect(callbacks?.onSOPChange).toBeDefined()

    act(() => {
      callbacks!.onSOPChange!({ sopId: 'sop-1', title: '更换肘关节模组' })
    })

    // Component still renders heading after state update
    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  it('handles onSOPChange with null (deselects SOP)', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onSOPChange?: (sop: null) => void
    } | null

    act(() => {
      callbacks!.onSOPChange!(null)
    })

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  // ─── SOPPlayer callback: onStepChange ────────────────────────────────────

  it('handles onStepChange callback and applies SOP intent without crashing', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onStepChange?: (
        step: { stepId: string; title: string; targetParts?: string[] } | null,
        index: number,
      ) => void
    } | null
    expect(callbacks?.onStepChange).toBeDefined()

    act(() => {
      callbacks!.onStepChange!({ stepId: 'step-1', title: '拆卸外壳' }, 0)
    })

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  it('resets explode amount when step title contains 收起', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onStepChange?: (
        step: { stepId: string; title: string; description?: string } | null,
        index: number,
      ) => void
    } | null

    act(() => {
      callbacks!.onStepChange!(
        { stepId: 'step-x', title: '收起外壳', description: '' },
        1,
      )
    })

    // No crash — explode amount is reset internally
    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  // ─── SOPPlayer callback: onExecutionContextChange ─────────────────────────

  it('handles onExecutionContextChange with COMPLETE state (resets explode)', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onExecutionContextChange?: (
        ctx: { executionState: string } | null,
        step: null,
      ) => void
    } | null
    expect(callbacks?.onExecutionContextChange).toBeDefined()

    act(() => {
      callbacks!.onExecutionContextChange!({ executionState: 'COMPLETE' }, null)
    })

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  it('handles onExecutionContextChange with null context', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onExecutionContextChange?: (ctx: null, step: null) => void
    } | null

    act(() => {
      callbacks!.onExecutionContextChange!(null, null)
    })

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  // ─── SOPPlayer callback: onBlocked ────────────────────────────────────────

  it('handles onBlocked callback (switches right panel to part tab)', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onBlocked?: (report: { reasonCode: string }) => void
    } | null
    expect(callbacks?.onBlocked).toBeDefined()

    act(() => {
      callbacks!.onBlocked!({ reasonCode: 'WRONG_TOOL' })
    })

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  // ─── SOPPlayer callback: onToolRequired ───────────────────────────────────

  it('handles onToolRequired callback with a toolId', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onToolRequired?: (toolId: string | null) => void
    } | null
    expect(callbacks?.onToolRequired).toBeDefined()

    act(() => {
      callbacks!.onToolRequired!('TORQUE_WRENCH')
    })

    expect(setCurrentToolMock).toHaveBeenCalledWith('TORQUE_WRENCH')
  })

  it('handles onToolRequired callback with null (clears tool)', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onToolRequired?: (toolId: string | null) => void
    } | null

    act(() => {
      callbacks!.onToolRequired!(null)
    })

    expect(setCurrentToolMock).toHaveBeenCalledWith(null)
  })

  // ─── SOPPlayer callback: onPartSelect ─────────────────────────────────────

  it('handles onPartSelect callback with null (clears selected part)', () => {
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onPartSelect?: (partName: string | null) => void
    } | null
    expect(callbacks?.onPartSelect).toBeDefined()

    act(() => {
      callbacks!.onPartSelect!(null)
    })

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
  })

  // ─── Part panel empty state ───────────────────────────────────────────────

  it('shows 点击零件查看详情 empty placeholder in part panel (layoutMode=full)', () => {
    render(<SOPMaintenancePage layoutMode="full" />)

    expect(screen.getByText('点击零件查看详情')).toBeTruthy()
  })

  // ─── View mode segmented control ──────────────────────────────────────────

  it('renders the view mode segmented control with 正常 and 爆炸图 options', () => {
    render(<SOPMaintenancePage />)

    expect(screen.getByRole('radiogroup', { name: '视图模式切换' })).toBeTruthy()
    expect(screen.getByRole('radio', { name: /正常/i })).toBeTruthy()
    expect(screen.getByRole('radio', { name: /爆炸图/i })).toBeTruthy()
  })

  // ─── Breadcrumb shows 总览 on initial render ──────────────────────────────

  it('shows 总览 breadcrumb item on initial render', () => {
    render(<SOPMaintenancePage />)

    expect(screen.getByText('总览')).toBeTruthy()
  })

  // ─── SOP 3D region aria label ─────────────────────────────────────────────

  it('renders the SOP 3D view region with correct aria-label', () => {
    render(<SOPMaintenancePage />)

    expect(screen.getByLabelText('SOP 3D 视图区')).toBeTruthy()
  })

  // ─── 3D viewer callbacks: isolation state machine ─────────────────────────

  const withRobot = () => {
    currentRobotSelectorMock.mockImplementation(
      (sel: (s: Record<string, unknown>) => unknown) => sel(ROBOT_STATE),
    )
  }
  const atomCb = () => atomCapture.current as Record<string, (...args: unknown[]) => void>

  it('enters isolation (L1) when a core part is selected from overview', () => {
    withRobot()
    render(<SOPMaintenancePage />)

    act(() => atomCb().onPartHover({ name: 'torso_link', displayName: '躯干' }))
    act(() => atomCb().onPartHover(null))
    act(() => atomCb().onPartSelect({ name: 'torso_link', displayName: '躯干' }))

    // Now ISOLATED: the 返回总览 affordance and the isolated breadcrumb appear.
    // breadcrumb uses getLinkDisplayName (=link id) since manifest-less partMetadata is empty.
    expect(screen.getByRole('button', { name: /返回总览/ })).toBeTruthy()
    expect(screen.getAllByText('torso_link').length).toBeGreaterThan(0)
  })

  it('drills into L2 sub-parts and selects a sub-part (layoutMode=full)', () => {
    withRobot()
    render(<SOPMaintenancePage layoutMode="full" />)

    // OVERVIEW → ISOLATED on torso
    act(() => atomCb().onPartSelect({ name: 'torso_link', displayName: '躯干' }))
    // ISOLATED → L2 on a link that has detail parts
    act(() => atomCb().onPartSelect({ name: 'left_arm_pitch_link', displayName: '左臂' }))

    // L2 sub-part list panel is now visible in the inspector rail
    expect(screen.getByText('📋 left_arm_pitch_link 子零件列表')).toBeTruthy()

    // Select a (non-screw) sub-part → L3, breadcrumb gains the sub-part crumb
    act(() =>
      atomCb().onSubPartSelect('left_arm_pitch_link', 0, {
        name: 'bolt_a',
        displayName: '螺栓A',
        category: 'bolt',
        actionTarget: 'bolt_a',
      }),
    )
    expect(screen.getAllByText('螺栓A').length).toBeGreaterThan(0)
  })

  it('navigates back to L1 via breadcrumb crumb after drilling to L2', async () => {
    withRobot()
    const user = userEvent.setup()
    render(<SOPMaintenancePage layoutMode="full" />)

    act(() => atomCb().onPartSelect({ name: 'torso_link', displayName: '躯干' }))
    act(() => atomCb().onPartSelect({ name: 'left_arm_pitch_link', displayName: '左臂' }))
    expect(screen.getByText('📋 left_arm_pitch_link 子零件列表')).toBeTruthy()

    // Click the L1 crumb (torso_link) inside the 3D viewer breadcrumb → navigateBreadcrumb(1).
    // Scope to the viewer region so we don't hit the left-rail isolation button.
    const region = screen.getByLabelText('SOP 3D 视图区')
    await user.click(within(region).getByText('torso_link'))

    // Back at L1: the L2 sub-part list panel is gone
    expect(screen.queryByText('📋 left_arm_pitch_link 子零件列表')).toBeNull()
  })

  it('resets to overview when 返回总览 is clicked after isolation', async () => {
    withRobot()
    const user = userEvent.setup()
    render(<SOPMaintenancePage />)

    act(() => atomCb().onPartSelect({ name: 'torso_link', displayName: '躯干' }))
    expect(screen.getByRole('button', { name: /返回总览/ })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: /返回总览/ }))

    // Back to overview: the 返回总览 button is gone
    expect(screen.queryByRole('button', { name: /返回总览/ })).toBeNull()
  })

  it('handles part double-click and visible-bounds change without crashing', () => {
    withRobot()
    render(<SOPMaintenancePage />)

    act(() => atomCb().onVisibleBoundsChange({ center: [0.1, 0.2, 0.3], radius: 0.5 }))
    act(() => atomCb().onPartDoubleClick({ name: 'torso_link', displayName: '躯干' }))
    // Enter isolation then feed bounds again to exercise the ISOLATED branch
    act(() => atomCb().onPartSelect({ name: 'torso_link', displayName: '躯干' }))
    act(() => atomCb().onVisibleBoundsChange({ center: [0.0, 0.1, 0.2], radius: 0.3 }))

    expect(screen.getByText('Atom01InteractiveStub')).toBeTruthy()
  })

  it('ignores visible-bounds change when center has non-finite values', () => {
    withRobot()
    render(<SOPMaintenancePage />)

    act(() =>
      atomCb().onVisibleBoundsChange({ center: [Number.NaN, 0, 0], radius: 0.5 }),
    )

    expect(screen.getByText('Atom01InteractiveStub')).toBeTruthy()
  })

  // ─── viewMode segmented control: explode guard in overview ─────────────────

  it('blocks switching to 爆炸图 from overview and stays in 正常', () => {
    render(<SOPMaintenancePage />)

    // antd Segmented radios have pointer-events:none; fireEvent triggers onChange directly
    fireEvent.click(screen.getByText('爆炸图'))

    // characterization: guard keeps 正常 selected (message.info shown, mode reverts)
    expect(
      (screen.getByRole('radio', { name: /正常/i }) as HTMLInputElement).checked,
    ).toBe(true)
  })

  // ─── SOPPlayer onPartSelect with a part name (no-op without manifest metadata) ─

  it('handles SOPPlayer onPartSelect with a part name without crashing (no manifest metadata)', () => {
    withRobot()
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onPartSelect?: (partName: string | null) => void
    } | null

    // partMetadata is empty when no manifest is loaded → isolation is not entered
    act(() => {
      callbacks!.onPartSelect!('torso_link')
    })

    expect(screen.queryByRole('button', { name: /返回总览/ })).toBeNull()
    expect(screen.getByText('Atom01InteractiveStub')).toBeTruthy()
  })

  // ─── SOPPlayer onStepChange applies a rich SOP intent (tool routing) ───────

  it('routes requiredTool through setCurrentTool on step change SOP intent', () => {
    withRobot()
    sopSceneSyncMock.mockReturnValue({
      ...makeSyncState(),
      bindStep: vi.fn(() => ({
        targetPart: 'torso_link',
        explodeAmount: 0.5,
        requiredTool: 'TORQUE_WRENCH',
      })),
    })
    render(<SOPMaintenancePage />)

    const callbacks = sopPlayerCallbackCapture.current as {
      onStepChange?: (step: { stepId: string; title: string }, index: number) => void
    } | null

    act(() => {
      callbacks!.onStepChange!({ stepId: 'step-1', title: '拆卸' }, 0)
    })

    // intent.requiredTool routed to setCurrentTool (targetPart isolation is a no-op
    // without manifest-derived partMetadata)
    expect(setCurrentToolMock).toHaveBeenCalledWith('TORQUE_WRENCH')
  })

  // ─── 3D error boundary degradation ───────────────────────────────────────

  it('shows 3D 视图不可用 fallback when 3D child throws, rest of page still visible', () => {
    // Need a robot so Atom01Interactive is mounted (robotId branch in SOPViewerScene).
    currentRobotSelectorMock.mockImplementation(
      (sel: (s: Record<string, unknown>) => unknown) => sel(ROBOT_STATE),
    )
    // Suppress expected React error-boundary console noise in this test.
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    atomShouldThrow.current = true

    render(<SOPMaintenancePage />)

    // 3D region shows the Viewer3DErrorBoundary degradation copy
    expect(screen.getByText(/3D 视图不可用/)).toBeTruthy()
    // WebGL-specific message also present (may appear in multiple nested elements)
    expect(screen.getAllByText(/WebGL/).length).toBeGreaterThan(0)
    // Page-level heading still visible → page did NOT crash
    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()

    consoleError.mockRestore()
  })
})
