import { Children, isValidElement } from 'react'
import { render, screen } from '@testing-library/react'
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

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children?: React.ReactNode }) => (
    <div>
      {Children.map(children, (child) => {
        if (!isValidElement(child)) {
          return child ?? 'CanvasStub'
        }
        return typeof child.type === 'string' ? null : child
      })}
    </div>
  ),
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
  SOPPlayerAdjudicated: ({ availableSOPs }: { availableSOPs: Array<{ title: string }> }) => (
    <div>
      SOPPlayerStub
      {availableSOPs.map((sop) => (
        <div key={sop.title}>{sop.title}</div>
      ))}
    </div>
  ),
}))

vi.mock('@/hooks/useSOPScripts', () => ({
  useSOPScripts: () => ({
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
  }),
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
  ActionType: {
    SELECT_TOOL: 'SELECT_TOOL',
    FOCUS_CAMERA: 'FOCUS_CAMERA',
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
import { writeMaintenanceWorkspaceSession } from '@/features/maintenance/runtimeWorkspaceSession'

describe('SOPMaintenancePage runtime draft flow', () => {
  beforeEach(() => {
    setOperationModeMock.mockReset()
    setCurrentToolMock.mockReset()
    preloadAllPartsMock.mockReset()
    clientGetMock.mockReset()
    clientPostMock.mockReset()
    navigateMock.mockReset()
    window.sessionStorage.clear()

    writeMaintenanceWorkspaceSession({
      projectId: 'project-fourier-n1',
      projectLabel: 'Fourier N1 runtime',
      maintenanceGoal: '执行器弯曲维护',
      focusArea: '肘关节',
      draft: {
        draft_id: 'draft-runtime-001',
        project_id: 'project-fourier-n1',
        request_id: 'req-runtime-001',
        review_status: 'draft_pending_review',
        draft: {
          title: 'Fourier N1 肘关节维保',
          maintenance_goal: '执行器弯曲维护',
          steps: [
            {
              step_id: 'step_001',
              title: '检查肘关节温度',
              description: '确认目标模组无异常温升',
              model_targets: ['elbow_joint'],
            },
          ],
          review_notes: ['part mapping requires review: elbow_joint'],
        },
        verdict_steps: [
          {
            stepId: 'step_001',
            title: '检查肘关节温度',
          },
        ],
        viewer_manifest: {
          robotId: 'fourier-n1-runtime',
          label: 'Fourier N1',
          parts: ['viewer/elbow.glb'],
          assets: [
            {
              asset_id: 'elbow_joint::viewer/elbow.glb',
              asset_type: 'gltf',
              node_id: 'elbow_joint',
              path: 'viewer/elbow.glb',
              source_paths: ['viewer/elbow.glb'],
            },
          ],
          needs_review_nodes: ['elbow_joint'],
        },
        manifest_tree: {
          robot_key: 'fourier-n1-runtime',
          root_nodes: ['elbow_joint'],
          nodes: [
            {
              id: 'elbow_joint',
              display_name: 'elbow_joint',
              parent_id: null,
              children: [],
              source_paths: ['viewer/elbow.glb'],
              runtime_asset_paths: ['viewer/elbow.glb'],
              file_kinds: ['viewer_asset'],
            },
          ],
        },
        manifest_mapping: {
          elbow_joint: {
            source_paths: ['viewer/elbow.glb'],
            runtime_asset_paths: ['viewer/elbow.glb'],
            file_kinds: ['viewer_asset'],
          },
        },
        citations: [
          {
            title: '执行器维护说明',
            source: 'semantic',
          },
        ],
      },
    })
  })

  it('hydrates runtime maintenance draft from the dedicated project draft page session', async () => {
    render(<SOPMaintenancePage />)

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '项目草案页' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '打开检视页' })).toBeTruthy()
    expect(screen.queryByText('机器人项目与 AI 草案')).toBeNull()
    expect(screen.queryByText('执行页仅保留步骤、工具、播放器与 3D 操作区')).toBeNull()

    expect((await screen.findAllByText('Fourier N1 肘关节维保')).length).toBeGreaterThan(0)
    expect(screen.getByText('RuntimeAssetPreviewStub')).toBeTruthy()
  })
})
