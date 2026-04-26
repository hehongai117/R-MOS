import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AgentWorkbenchPage from '@/pages/agent/AgentWorkbenchPage';

const { sendAgentRequestV2Mock, getTraceEventsMock, runDiagnosisActionMock, setWorkbenchCapsuleMock } = vi.hoisted(() => ({
  sendAgentRequestV2Mock: vi.fn(),
  getTraceEventsMock: vi.fn(),
  runDiagnosisActionMock: vi.fn(),
  setWorkbenchCapsuleMock: vi.fn(),
}));
const mockTelemetryPayload = {
  joints: [
    {
      joint_id: 'waist',
      position: 0,
      velocity: 0,
      torque: 0.1,
      temperature: 76,
      error_code: 'E002_STALL',
    },
  ],
  sensors: {
    battery: 82,
    temperature: 45,
    voltage: { main: 24 },
  },
  active_faults: ['E002_STALL'],
};

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock);
vi.stubGlobal('getComputedStyle', () => ({
  getPropertyValue: () => '',
}));

vi.mock('@/api/agent-v2', () => ({
  sendAgentRequestV2: sendAgentRequestV2Mock,
  getTraceEvents: getTraceEventsMock,
  runDiagnosisAction: runDiagnosisActionMock,
}));

vi.mock('@/components/Agent/AgentStatusCapsule', () => ({
  setWorkbenchCapsule: setWorkbenchCapsuleMock,
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    status: 'connected',
    isConnected: true,
    isDataStale: false,
    telemetryData: mockTelemetryPayload,
    lastUpdateTime: new Date('2026-03-08T12:00:00Z'),
    error: null,
    retryCount: 0,
    reconnect: vi.fn(),
  }),
}));

describe('AgentWorkbenchPage', () => {
  beforeEach(() => {
    sendAgentRequestV2Mock.mockReset();
    getTraceEventsMock.mockReset();
    runDiagnosisActionMock.mockReset();
    setWorkbenchCapsuleMock.mockReset();
    window.sessionStorage.clear();
  });

  it('submits quick action prompt with matched intent', async () => {
    sendAgentRequestV2Mock.mockResolvedValue({
      success: true,
      trace_id: 'trace-quick-action',
      message: '已创建维保任务',
      confidence: 'high',
      evidence_refs: [],
      from_cache: false,
      timestamp: Date.now(),
      policy_decision: {
        allowed: true,
        risk_level: 'R1',
        requires_approval: false,
        evidence_required: [],
      },
    });

    const user = userEvent.setup();
    render(<AgentWorkbenchPage />);

    expect(screen.queryByText('快捷操作')).toBeNull();
    expect(screen.getAllByRole('button', { name: /派单维保/ })).toHaveLength(1);
    expect(screen.getAllByRole('button', { name: /查看任务/ })).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: '派单维保' }));

    await waitFor(() => {
      expect(sendAgentRequestV2Mock).toHaveBeenCalledTimes(1);
    });
    expect(sendAgentRequestV2Mock).toHaveBeenCalledWith(
      expect.objectContaining({
        message: '请为我创建一个维保派单，并给出执行步骤。',
        intent_classification: 'execute-task',
      })
    );
    await waitFor(() => {
      expect(screen.getByText('已创建维保任务')).toBeTruthy();
    });
  });

  it('updates policy decision card and capsule for approval-required response', async () => {
    sendAgentRequestV2Mock.mockResolvedValue({
      success: true,
      trace_id: 'trace-approval',
      message: '该请求需要审批后执行',
      confidence: 'high',
      evidence_refs: [],
      from_cache: false,
      timestamp: Date.now(),
      policy_decision: {
        allowed: true,
        risk_level: 'R2',
        requires_approval: true,
        approval_level: 'L2',
        evidence_required: [],
      },
    });

    const user = userEvent.setup();
    render(<AgentWorkbenchPage />);

    await user.type(screen.getByPlaceholderText('告诉我你的需求…'), '执行高风险任务');
    await user.click(screen.getByRole('button', { name: /发送/ }));

    await waitFor(() => {
      expect(screen.getByText(/需审批 L2/)).toBeTruthy();
    });
    expect(setWorkbenchCapsuleMock).toHaveBeenCalledWith(
      expect.objectContaining({
        state: 'WAITING_APPROVAL',
      })
    );
  });

  it('opens trace drawer and renders events', async () => {
    sendAgentRequestV2Mock.mockResolvedValue({
      success: true,
      trace_id: 'trace-1',
      message: '已完成',
      confidence: 'high',
      evidence_refs: [],
      from_cache: false,
      timestamp: Date.now(),
      policy_decision: {
        allowed: true,
        risk_level: 'R0',
        requires_approval: false,
        evidence_required: [],
      },
    });
    getTraceEventsMock.mockResolvedValue({
      trace_id: 'trace-1',
      events: [{ event_type: 'policy_checked', status: 'ok' }],
    });

    const user = userEvent.setup();
    render(<AgentWorkbenchPage />);

    await user.type(screen.getByPlaceholderText('告诉我你的需求…'), '查看轨迹');
    await user.click(screen.getByRole('button', { name: /发送/ }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'trace' })).toBeTruthy();
    });
    await user.click(screen.getByRole('button', { name: 'trace' }));

    await waitFor(() => {
      expect(getTraceEventsMock).toHaveBeenCalledWith('trace-1');
    });
    await waitFor(() => {
      expect(screen.getByText('policy_checked')).toBeTruthy();
    });
  });

  it('renders structured diagnosis result when diagnoser returns maintenance plan', async () => {
    sendAgentRequestV2Mock.mockResolvedValue({
      success: true,
      trace_id: 'trace-diagnosis',
      message: '诊断完成',
      confidence: 'high',
      evidence_refs: [],
      from_cache: false,
      timestamp: Date.now(),
      policy_decision: {
        allowed: true,
        risk_level: 'R1',
        requires_approval: false,
        evidence_required: [],
      },
      result: {
        diagnosis: {
          success: true,
          primary_hypothesis: {
            fault_code: 'E002_STALL',
            fault_name: '电机堵转',
            confidence: 0.91,
            affected_parts: ['waist'],
            possible_causes: ['机械卡滞'],
            evidence: { joint_id: 'waist' },
          },
          alternative_hypotheses: [],
          requires_supervisor: true,
          reasoning: '关节速度接近 0，符合堵转特征。',
          recommended_actions: ['检查减速器'],
          error_message: null,
        },
        maintenance_plan: {
          success: true,
          plan_id: 'plan-001',
          fault_code: 'E002_STALL',
          fault_name: '电机堵转',
          actions: [
            {
              action_id: 'A-1',
              action_type: 'CHECK',
              target_part: 'waist',
              description: '检查机械卡滞',
              estimated_duration_minutes: 10,
              required_tools: ['扭矩扳手'],
              safety_warnings: ['先断电'],
            },
          ],
          total_duration_minutes: 10,
          requires_supervisor: true,
          validation_required: true,
          error_message: null,
        },
        verification: {
          success: true,
          plan_id: 'plan-001',
          before_state: { fault_count: 1 },
          after_state: { fault_count: 0 },
          delta_summary: { fault_count: '1 -> 0' },
          verdict: '验证通过',
          failed_steps: [],
        },
      },
    });

    const user = userEvent.setup();
    render(<AgentWorkbenchPage />);

    await user.click(screen.getByRole('button', { name: '诊断问题' }));

    await waitFor(() => {
      expect(screen.getByText('诊断完成')).toBeTruthy();
    });
    await waitFor(() => {
      expect(screen.getByText('电机堵转')).toBeTruthy();
    });
    expect(screen.getByText('仿真验证')).toBeTruthy();
    expect(screen.getByText('关键变化')).toBeTruthy();
    expect(screen.getByText('故障数量')).toBeTruthy();
    expect(screen.queryByText('fault_count')).toBeNull();
    expect(sendAgentRequestV2Mock).toHaveBeenCalledWith(
      expect.objectContaining({
        intent_classification: 'delegate-diagnoser',
        telemetry_payload: mockTelemetryPayload,
      })
    );
    expect(window.sessionStorage.getItem('latest-diagnosis-result')).toContain('E002_STALL');
  });

  it('confirms diagnosis execution through backend action api', async () => {
    sendAgentRequestV2Mock.mockResolvedValue({
      success: true,
      trace_id: 'trace-confirm',
      message: '诊断完成',
      confidence: 'high',
      evidence_refs: [],
      from_cache: false,
      timestamp: Date.now(),
      policy_decision: {
        allowed: true,
        risk_level: 'R1',
        requires_approval: false,
        evidence_required: [],
      },
      result: {
        diagnosis: {
          success: true,
          primary_hypothesis: {
            fault_code: 'E002_STALL',
            fault_name: '电机堵转',
            confidence: 0.91,
            affected_parts: ['waist'],
            possible_causes: ['机械卡滞'],
            evidence: { joint_id: 'waist' },
          },
          alternative_hypotheses: [],
          requires_supervisor: false,
          reasoning: '关节速度接近 0，符合堵转特征。',
          recommended_actions: ['检查减速器'],
          error_message: null,
        },
        maintenance_plan: {
          success: true,
          plan_id: 'plan-002',
          fault_code: 'E002_STALL',
          fault_name: '电机堵转',
          actions: [
            {
              action_id: 'A-1',
              action_type: 'CHECK',
              target_part: 'waist',
              description: '检查机械卡滞',
              estimated_duration_minutes: 10,
              required_tools: ['扭矩扳手'],
              safety_warnings: ['先断电'],
            },
          ],
          total_duration_minutes: 10,
          requires_supervisor: false,
          validation_required: true,
          error_message: null,
        },
        verification: {
          success: true,
          plan_id: 'plan-002',
          before_state: { fault_count: 1 },
          after_state: { fault_count: 0 },
          delta_summary: { fault_count: '1 -> 0' },
          verdict: '验证通过',
          failed_steps: [],
        },
      },
    });
    runDiagnosisActionMock.mockResolvedValue({
      trace_id: 'trace-confirm',
      action: 'confirm_execution',
      message: '已确认执行方案，请转入 SOP 工作台执行。',
      recorded: true,
    });

    const user = userEvent.setup();
    render(<AgentWorkbenchPage />);

    await user.click(screen.getByRole('button', { name: '诊断问题' }));

    await waitFor(() => {
      expect((screen.getByRole('button', { name: '确认执行方案' }) as HTMLButtonElement).disabled).toBe(false);
    });
    await user.click(screen.getByRole('button', { name: '确认执行方案' }));

    await waitFor(() => {
      expect(runDiagnosisActionMock).toHaveBeenCalledWith('trace-confirm', 'confirm_execution');
    });
    await waitFor(() => {
      expect(screen.getByText('已确认执行方案，请转入 SOP 工作台执行。')).toBeTruthy();
    });
  });

  it('escalates diagnosis result through backend action api', async () => {
    sendAgentRequestV2Mock.mockResolvedValue({
      success: true,
      trace_id: 'trace-escalate',
      message: '诊断完成',
      confidence: 'high',
      evidence_refs: [],
      from_cache: false,
      timestamp: Date.now(),
      policy_decision: {
        allowed: true,
        risk_level: 'R1',
        requires_approval: false,
        evidence_required: [],
      },
      result: {
        diagnosis: {
          success: true,
          primary_hypothesis: {
            fault_code: 'E002_STALL',
            fault_name: '电机堵转',
            confidence: 0.91,
            affected_parts: ['waist'],
            possible_causes: ['机械卡滞'],
            evidence: { joint_id: 'waist' },
          },
          alternative_hypotheses: [],
          requires_supervisor: true,
          reasoning: '关节速度接近 0，符合堵转特征。',
          recommended_actions: ['检查减速器'],
          error_message: null,
        },
        maintenance_plan: {
          success: true,
          plan_id: 'plan-003',
          fault_code: 'E002_STALL',
          fault_name: '电机堵转',
          actions: [
            {
              action_id: 'A-1',
              action_type: 'CHECK',
              target_part: 'waist',
              description: '检查机械卡滞',
              estimated_duration_minutes: 10,
              required_tools: ['扭矩扳手'],
              safety_warnings: ['先断电'],
            },
          ],
          total_duration_minutes: 10,
          requires_supervisor: true,
          validation_required: true,
          error_message: null,
        },
        verification: {
          success: true,
          plan_id: 'plan-003',
          before_state: { fault_count: 1 },
          after_state: { fault_count: 0 },
          delta_summary: { fault_count: '1 -> 0' },
          verdict: '验证通过',
          failed_steps: [],
        },
      },
    });
    runDiagnosisActionMock.mockResolvedValue({
      trace_id: 'trace-escalate',
      action: 'escalate_to_teacher',
      message: '已上报教师审核，请等待处理。',
      recorded: true,
    });

    const user = userEvent.setup();
    render(<AgentWorkbenchPage />);

    await user.click(screen.getByRole('button', { name: '诊断问题' }));

    await waitFor(() => {
      expect((screen.getByRole('button', { name: '上报教师审核' }) as HTMLButtonElement).disabled).toBe(false);
    });
    await user.click(screen.getByRole('button', { name: '上报教师审核' }));

    await waitFor(() => {
      expect(runDiagnosisActionMock).toHaveBeenCalledWith('trace-escalate', 'escalate_to_teacher');
    });
    await waitFor(() => {
      expect(screen.getByText('已上报教师审核，请等待处理。')).toBeTruthy();
    });
  });
});
