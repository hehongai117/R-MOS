import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { VerifyChecklistPanel } from '../VerifyChecklistPanel';

const items = [
    { key: 'gap', label: '外观间隙复核', expected: '间隙 ≤ 0.5mm' },
    { key: 'torque', label: '紧固扭矩复核', expected: '扭矩 2.5N·m' },
];

describe('验收记录面板', () => {
    it('显示验收项及期望值', () => {
        render(<VerifyChecklistPanel items={items} confirmed={[]} onChange={() => {}} />);
        expect(screen.getByText('外观间隙复核')).toBeInTheDocument();
        expect(screen.getByText('间隙 ≤ 0.5mm')).toBeInTheDocument();
    });

    it('勾选后回调携带该验收项标识', () => {
        const onChange = vi.fn();
        render(<VerifyChecklistPanel items={items} confirmed={[]} onChange={onChange} />);
        fireEvent.click(screen.getByLabelText('确认 gap 验收通过'));
        expect(onChange).toHaveBeenCalledWith(['gap']);
    });

    it('全部勾选时显示验收完成', () => {
        render(<VerifyChecklistPanel items={items} confirmed={['gap', 'torque']} onChange={() => {}} />);
        expect(screen.getByText('验收完成')).toBeInTheDocument();
    });
});
