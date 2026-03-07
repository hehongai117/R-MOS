import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import AgentStatusCapsule, { setWorkbenchCapsule } from '@/components/Agent/AgentStatusCapsule';

describe('AgentStatusCapsule', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('renders capsule content after status update event', () => {
    render(<AgentStatusCapsule />);

    act(() => {
      setWorkbenchCapsule({
        state: 'WAITING_APPROVAL',
        title: '等待审批',
        detail: 'L2 级',
        action: '等待中…',
      });
    });

    expect(screen.getByText('等审批')).toBeTruthy();
    expect(screen.getByText('等待审批')).toBeTruthy();
    expect(screen.getByText('L2 级')).toBeTruthy();
    expect(screen.getByText('等待中…')).toBeTruthy();
  });

  it('clears capsule when payload is null', () => {
    render(<AgentStatusCapsule />);

    act(() => {
      setWorkbenchCapsule({
        state: 'BLOCKED',
        title: '策略阻断',
      });
    });
    expect(screen.getByText('阻塞')).toBeTruthy();

    act(() => {
      setWorkbenchCapsule(null);
    });

    expect(screen.queryByText('阻塞')).toBeNull();
    expect(sessionStorage.getItem('rmos_agent_status_capsule')).toBeNull();
  });
});
