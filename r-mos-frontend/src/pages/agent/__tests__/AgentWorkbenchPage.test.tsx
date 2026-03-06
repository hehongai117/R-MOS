import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AgentWorkbenchPage from '@/pages/agent/AgentWorkbenchPage';

const { sendAgentRequestV2Mock, getTraceEventsMock, setWorkbenchCapsuleMock } = vi.hoisted(() => ({
  sendAgentRequestV2Mock: vi.fn(),
  getTraceEventsMock: vi.fn(),
  setWorkbenchCapsuleMock: vi.fn(),
}));

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock);

vi.mock('@/api/agent-v2', () => ({
  sendAgentRequestV2: sendAgentRequestV2Mock,
  getTraceEvents: getTraceEventsMock,
}));

vi.mock('@/components/Agent/AgentStatusCapsule', () => ({
  setWorkbenchCapsule: setWorkbenchCapsuleMock,
}));

describe('AgentWorkbenchPage', () => {
  beforeEach(() => {
    sendAgentRequestV2Mock.mockReset();
    getTraceEventsMock.mockReset();
    setWorkbenchCapsuleMock.mockReset();
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

    await user.click(screen.getAllByRole('button', { name: /派单维保/ })[0]);
    await user.click(screen.getByRole('button', { name: /发送/ }));

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
});
