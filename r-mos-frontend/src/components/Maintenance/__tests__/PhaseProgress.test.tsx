import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PhaseProgress } from '../sopPlayer/PhaseProgress';

describe('三段进度条', () => {
    const progress = [
        { phase: 'prep' as const, total: 4, completed: 4, unlocked: true },
        { phase: 'execute' as const, total: 14, completed: 3, unlocked: true },
        { phase: 'verify' as const, total: 4, completed: 0, unlocked: false },
    ];

    it('渲染三段中文标签与完成计数', () => {
        render(<PhaseProgress progress={progress} currentPhase="execute" />);
        expect(screen.getByText('准备')).toBeInTheDocument();
        expect(screen.getByText('执行')).toBeInTheDocument();
        expect(screen.getByText('验证')).toBeInTheDocument();
        expect(screen.getByText('3/14')).toBeInTheDocument();
    });

    it('标记未解锁段且单阶段 SOP 不渲染进度条', () => {
        const { rerender } = render(
            <PhaseProgress progress={progress} currentPhase="execute" />,
        );
        expect(screen.getByLabelText('验证 阶段未解锁')).toBeInTheDocument();

        rerender(<PhaseProgress progress={[progress[1]]} currentPhase="execute" />);
        expect(screen.queryByText('执行')).not.toBeInTheDocument();
    });
});
