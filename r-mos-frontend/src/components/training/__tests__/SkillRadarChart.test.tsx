import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SkillRadarChart } from '@/components/training/SkillRadarChart';

describe('SkillRadarChart', () => {
  it('renders five dimensions from student_skill_profiles data', () => {
    render(
      <SkillRadarChart
        profile={{
          safety: 88,
          quality: 79,
          efficiency: 84,
          diagnosis: 73,
          collaboration: 91,
        }}
      />
    );

    expect(screen.getByTestId('radar-item-safety').textContent).toContain('88');
    expect(screen.getByTestId('radar-item-quality').textContent).toContain('79');
    expect(screen.getByTestId('radar-item-efficiency').textContent).toContain('84');
    expect(screen.getByTestId('radar-item-diagnosis').textContent).toContain('73');
    expect(screen.getByTestId('radar-item-collaboration').textContent).toContain('91');
  });
});
