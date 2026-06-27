import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionType, PreconditionType } from '@/adjudication'
import type { SOPScriptAdjudication, SOPStepAdjudication } from '@/adjudication'

// ---------------------------------------------------------------------------
// Peripheral mocks. The adjudication engine itself (createSOPExecutor + store)
// is REAL — it is pure logic and is exactly the behavior we want to characterize.
// We only stub things that reach out of process or pull heavy unrelated trees:
//   - AIAssistantPanel (its own API/store deps are out of scope here)
//   - @/api/pipeline   (backend HTTP, fire-and-forget)
//   - useNavigate      (router side effect)
// ---------------------------------------------------------------------------
const navigateMock = vi.fn()

// antd Steps/Select/Modal touch matchMedia + ResizeObserver under jsdom.
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

vi.mock('@/components/AIAssistant/AIAssistantPanel', () => ({
  AIAssistantPanel: () => <div data-testid="ai-assistant-stub" />,
}))

vi.mock('@/api/pipeline', () => ({
  completeStep: vi.fn().mockResolvedValue({}),
  completeTask: vi.fn().mockResolvedValue({ report_generation: 'none', task_id: 1 }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

// ---------------------------------------------------------------------------
import { SOPPlayerAdjudicated } from '@/components/Maintenance/SOPPlayerAdjudicated'
import { useAdjudicationStore } from '@/adjudication'

// ---------------------------------------------------------------------------
// SOP fixtures
// ---------------------------------------------------------------------------
const makeStep = (
  index: number,
  over: Partial<SOPStepAdjudication> = {},
): SOPStepAdjudication =>
  ({
    stepId: `step_${index}`,
    stepIndex: index,
    title: `步骤${index}`,
    description: `步骤${index}的说明`,
    action: ActionType.FOCUS_CAMERA,
    targetParts: [],
    requiredTool: null,
    preconditions: [],
    validations: [],
    failureReasons: [],
    onSuccess: { nextStepId: `step_${index + 1}`, stateTransition: null },
    onFailure: { action: 'block', message: '操作被阻断' },
    ...over,
  }) as SOPStepAdjudication

const makeSOP = (
  steps: SOPStepAdjudication[],
  over: Partial<SOPScriptAdjudication> = {},
): SOPScriptAdjudication =>
  ({
    sopId: 'sop-1',
    title: '更换肘关节模组',
    version: '1.0',
    targetModule: 'left_elbow',
    estimatedTime: 600,
    difficulty: 'intermediate',
    steps,
    ...over,
  }) as SOPScriptAdjudication

// A two-step "document bridge" SOP: no targets / validations / tool → each step
// can be advanced by a single click (auto validate-and-advance).
const DOC_BRIDGE_SOP = makeSOP([makeStep(0), makeStep(1)])

const renderPlayer = (props: Partial<React.ComponentProps<typeof SOPPlayerAdjudicated>> = {}) =>
  render(
    <MemoryRouter>
      <SOPPlayerAdjudicated availableSOPs={[DOC_BRIDGE_SOP]} {...props} />
    </MemoryRouter>,
  )

describe('SOPPlayerAdjudicated characterization', () => {
  beforeEach(() => {
    navigateMock.mockReset()
    // Reset shared adjudication store between tests to avoid state bleed.
    useAdjudicationStore.getState().resetState()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the empty placeholder when no SOP is selected', () => {
    renderPlayer()

    expect(screen.getByText('选择一个 SOP 脚本开始')).toBeTruthy()
    expect(screen.getByText('SOP 播放器 (裁决级)')).toBeTruthy()
  })

  it('auto-selects a SOP from selectedSOPId prop and renders its steps + ready tag', () => {
    const onSOPChange = vi.fn()
    const onExecutorReady = vi.fn()
    renderPlayer({ selectedSOPId: 'sop-1', onSOPChange, onExecutorReady })

    // The IDLE state tag and step list appear
    expect(screen.getByText('就绪')).toBeTruthy()
    expect(screen.getAllByText('步骤0').length).toBeGreaterThan(0)
    expect(screen.getByText('步骤1')).toBeTruthy()
    // Loading the SOP wires up the executor + notifies the parent
    expect(onSOPChange).toHaveBeenCalledWith(DOC_BRIDGE_SOP)
    expect(onExecutorReady).toHaveBeenCalled()
  })

  it('auto-selects a SOP from initialSopId on mount', () => {
    renderPlayer({ initialSopId: 'sop-1' })

    expect(screen.getByText('就绪')).toBeTruthy()
  })

  it('advances through a document-bridge step when 下一步 is clicked', () => {
    const onStepChange = vi.fn()
    renderPlayer({ selectedSOPId: 'sop-1', onStepChange })

    // Initially at step 0 (0/2 completed)
    expect(screen.getByText('已完成: 0/2 步骤')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /下一步/ }))

    // Auto validate-and-advance completed step 0
    expect(screen.getByText('已完成: 1/2 步骤')).toBeTruthy()
    expect(onStepChange).toHaveBeenCalled()
  })

  it('labels the action button 完成 on the last step', () => {
    const lastOnly = makeSOP([makeStep(0)], { sopId: 'sop-last' })
    render(
      <MemoryRouter>
        <SOPPlayerAdjudicated availableSOPs={[lastOnly]} selectedSOPId="sop-last" />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: /完成/ })).toBeTruthy()
  })

  it('resets via 重置 and clears parent part/explode/tool outputs', () => {
    const onPartSelect = vi.fn()
    const onExplodeChange = vi.fn()
    const onToolRequired = vi.fn()
    renderPlayer({
      selectedSOPId: 'sop-1',
      onPartSelect,
      onExplodeChange,
      onToolRequired,
    })

    onPartSelect.mockClear()
    onExplodeChange.mockClear()
    onToolRequired.mockClear()

    // The 重置 button is icon-only inside a tooltip; it's the first control button.
    const resetBtn = screen.getAllByRole('button').find((b) => b.querySelector('.anticon-reload'))
    expect(resetBtn).toBeTruthy()
    fireEvent.click(resetBtn!)

    expect(onPartSelect).toHaveBeenCalledWith(null)
    expect(onExplodeChange).toHaveBeenCalledWith(0)
    expect(onToolRequired).toHaveBeenCalledWith(null)
  })

  it('enables 上一步 only after advancing past the first step', () => {
    renderPlayer({ selectedSOPId: 'sop-1' })

    const prevBtn = () => screen.getByRole('button', { name: /上一步/ }) as HTMLButtonElement
    expect(prevBtn().disabled).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: /下一步/ }))

    expect(prevBtn().disabled).toBe(false)

    // Going back is allowed only to completed steps
    fireEvent.click(prevBtn())
    expect(screen.getByText('就绪')).toBeTruthy()
  })

  it('deselects the SOP and returns to empty state when selectedSOPId becomes null', () => {
    const { rerender } = renderPlayer({ selectedSOPId: 'sop-1' })
    expect(screen.getByText('就绪')).toBeTruthy()

    rerender(
      <MemoryRouter>
        <SOPPlayerAdjudicated availableSOPs={[DOC_BRIDGE_SOP]} selectedSOPId={null} />
      </MemoryRouter>,
    )

    expect(screen.getByText('选择一个 SOP 脚本开始')).toBeTruthy()
  })

  it('enters EXECUTING with an action hint and a 手动验证 button', () => {
    // A tool-gated, target-less step: executeStep is ALLOWED (no preconditions /
    // no registered targets to adjudicate) but the requiredTool keeps it from the
    // doc-bridge auto-advance, so the player parks in EXECUTING.
    const toolStepSop = makeSOP(
      [
        makeStep(0, {
          action: ActionType.SELECT_TOOL,
          targetParts: [],
          requiredTool: 'hex_2.5',
          title: '选择工具',
        }),
        makeStep(1),
      ],
      { sopId: 'sop-exec' },
    )

    render(
      <MemoryRouter>
        <SOPPlayerAdjudicated availableSOPs={[toolStepSop]} selectedSOPId="sop-exec" />
      </MemoryRouter>,
    )

    // IDLE → click executes the step → EXECUTING (no auto-advance due to requiredTool)
    fireEvent.click(screen.getByRole('button', { name: /下一步/ }))

    expect(screen.getByText('执行中')).toBeTruthy()
    expect(
      screen.getByText('请完成当前步骤的检查与记录，点击“手动验证”继续。'),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: /手动验证/ })).toBeTruthy()
  })

  it('blocks the step and shows the alert + 重试 when a precondition fails', () => {
    const onBlocked = vi.fn()
    const blockedSop = makeSOP(
      [
        makeStep(0, {
          title: '需要先装备工具',
          preconditions: [
            {
              type: PreconditionType.TOOL_EQUIPPED,
              params: { toolId: 'hex_2.5' },
              errorMessage: '请先装备 hex_2.5 工具',
            },
          ],
        }),
        makeStep(1),
      ],
      { sopId: 'sop-blocked' },
    )

    render(
      <MemoryRouter>
        <SOPPlayerAdjudicated
          availableSOPs={[blockedSop]}
          selectedSOPId="sop-blocked"
          onBlocked={onBlocked}
        />
      </MemoryRouter>,
    )

    // IDLE → click executes the step → precondition fails → BLOCKED
    fireEvent.click(screen.getByRole('button', { name: /下一步/ }))

    expect(screen.getByText('已阻断')).toBeTruthy()
    expect(screen.getAllByText('操作被阻断').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /重试/ })).toBeTruthy()
    expect(onBlocked).toHaveBeenCalled()
  })

  it('executes a SELECT_TOOL step when a matching tool action event arrives', () => {
    const toolSop = makeSOP(
      [
        makeStep(0, {
          action: ActionType.SELECT_TOOL,
          requiredTool: 'hex_2.5',
        }),
        makeStep(1),
      ],
      { sopId: 'sop-tool' },
    )

    const { rerender } = render(
      <MemoryRouter>
        <SOPPlayerAdjudicated availableSOPs={[toolSop]} selectedSOPId="sop-tool" />
      </MemoryRouter>,
    )

    expect(screen.getByText('已完成: 0/2 步骤')).toBeTruthy()

    // Deliver a matching tool-selected action event → IDLE+SELECT_TOOL path executes + advances
    rerender(
      <MemoryRouter>
        <SOPPlayerAdjudicated
          availableSOPs={[toolSop]}
          selectedSOPId="sop-tool"
          actionEvent={{ seq: 1, type: 'tool_selected', toolId: 'hex_2.5' }}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('已完成: 1/2 步骤')).toBeTruthy()
  })
})
