import React from 'react';
import { Card, Checkbox, Space, Typography } from 'antd';
import type { RequiredPart } from '@/adjudication';
import { getToolById } from '@/data/toolData';

const { Text } = Typography;

export interface KitChecklistPanelProps {
    tools: string[];
    parts: RequiredPart[];
    confirmed: string[];
    onChange: (confirmed: string[]) => void;
}

export const KitChecklistPanel: React.FC<KitChecklistPanelProps> = ({
    tools,
    parts,
    confirmed,
    onChange,
}) => {
    const toggle = (id: string, checked: boolean) => {
        onChange(checked
            ? [...confirmed.filter(item => item !== id), id]
            : confirmed.filter(item => item !== id));
    };
    const remaining = [...tools, ...parts.map(part => part.bom_code)]
        .filter(id => !confirmed.includes(id)).length;

    return (
        <Card size="small" title="齐套检查">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {tools.length > 0 && (
                    <Space direction="vertical" size="small">
                        <Text strong>工具</Text>
                        {tools.map(id => (
                            <Checkbox
                                key={id}
                                checked={confirmed.includes(id)}
                                aria-label={`确认 ${id} 已备齐`}
                                onChange={event => toggle(id, event.target.checked)}
                            >
                                {getToolById(id)?.name ?? id}
                            </Checkbox>
                        ))}
                    </Space>
                )}

                {parts.length > 0 && (
                    <Space direction="vertical" size="small">
                        <Text strong>备件</Text>
                        {parts.map(part => (
                            <Checkbox
                                key={part.bom_code}
                                checked={confirmed.includes(part.bom_code)}
                                aria-label={`确认 ${part.bom_code} 已备齐`}
                                onChange={event => toggle(part.bom_code, event.target.checked)}
                            >
                                <Space size="small">
                                    <Text>{part.name}</Text>
                                    <Text type="secondary">
                                        ×{part.qty}{part.note ? ` ${part.note}` : ''}
                                    </Text>
                                </Space>
                            </Checkbox>
                        ))}
                    </Space>
                )}

                <Text type={remaining === 0 ? 'success' : 'warning'}>
                    {remaining === 0 ? '齐套完成' : `还有 ${remaining} 项待确认`}
                </Text>
            </Space>
        </Card>
    );
};

export default KitChecklistPanel;
