import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { WeakStepHeatmap } from '@/components/training/WeakStepHeatmap';

describe('WeakStepHeatmap', () => {
  it('maps fail count into heat levels and opens detail on click', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <WeakStepHeatmap
        steps={[
          { stepId: 's0', stepName: '准备工装', failCount: 0 },
          { stepId: 's1', stepName: '拆解电机盖', failCount: 2 },
          { stepId: 's2', stepName: '回装锁紧', failCount: 6 },
        ]}
        onStepSelect={onSelect}
      />
    );

    expect(screen.getByTestId('heat-step-s0').getAttribute('data-heat')).toBe('white');
    expect(screen.getByTestId('heat-step-s1').getAttribute('data-heat')).toBe('light-red');
    expect(screen.getByTestId('heat-step-s2').getAttribute('data-heat')).toBe('deep-red');

    await user.click(screen.getByRole('button', { name: /拆解电机盖/ }));
    expect(onSelect).toHaveBeenCalledWith('s1');
    expect(screen.getByText('步骤详情')).toBeTruthy();
    expect(screen.getAllByText(/拆解电机盖/).length).toBeGreaterThan(1);
  });
});
