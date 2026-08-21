import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KitChecklistPanel } from '../KitChecklistPanel';

const parts = [
    { bom_code: '6205-2RS', name: '深沟球轴承', qty: 1 },
    { bom_code: 'GREASE-01', name: '润滑脂', qty: 1, note: '薄层涂抹' },
];

describe('齐套检查面板', () => {
    it('列出工具与备件，显示数量', () => {
        render(<KitChecklistPanel tools={['hex_3']} parts={parts} confirmed={[]} onChange={() => {}} />);
        expect(screen.getByText('深沟球轴承')).toBeInTheDocument();
        expect(screen.getByText('×1')).toBeTruthy();
    });

    it('勾选后回调携带该项标识', () => {
        const onChange = vi.fn();
        render(<KitChecklistPanel tools={['hex_3']} parts={parts} confirmed={[]} onChange={onChange} />);
        fireEvent.click(screen.getByLabelText('确认 6205-2RS 已备齐'));
        expect(onChange).toHaveBeenCalledWith(['6205-2RS']);
    });

    it('未全部勾选时显示待确认数量', () => {
        render(<KitChecklistPanel tools={['hex_3']} parts={parts} confirmed={['hex_3']} onChange={() => {}} />);
        expect(screen.getByText(/还有 2 项待确认/)).toBeInTheDocument();
    });
});
