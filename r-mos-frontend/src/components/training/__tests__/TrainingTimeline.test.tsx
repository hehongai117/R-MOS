import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { TrainingTimeline } from '@/components/training/TrainingTimeline';

describe('TrainingTimeline', () => {
  it('renders records and filters by model', async () => {
    const user = userEvent.setup();

    render(
      <TrainingTimeline
        records={[
          { id: 'r1', model: 'FANUC-M20', score: 82, trainedAt: '2026-03-01' },
          { id: 'r2', model: 'ABB-120', score: 75, trainedAt: '2026-03-02' },
          { id: 'r3', model: 'FANUC-M20', score: 88, trainedAt: '2026-03-03' },
        ]}
      />
    );

    expect(screen.getAllByTestId('timeline-point').length).toBe(3);

    await user.selectOptions(screen.getByLabelText('机型筛选'), 'FANUC-M20');
    const filteredPoints = screen.getAllByTestId('timeline-point');
    expect(filteredPoints.length).toBe(2);
    expect(filteredPoints.every((node) => node.textContent?.includes('FANUC-M20'))).toBe(true);
  });
});
