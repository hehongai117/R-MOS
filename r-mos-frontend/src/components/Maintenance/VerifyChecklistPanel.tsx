import React from 'react';
import { Card, Checkbox, Space, Typography } from 'antd';

const { Text } = Typography;

export interface VerifyItem {
    key: string;
    label: string;
    expected?: string;
}

export interface VerifyChecklistPanelProps {
    items: VerifyItem[];
    confirmed: string[];
    onChange: (confirmed: string[]) => void;
}

export const VerifyChecklistPanel: React.FC<VerifyChecklistPanelProps> = ({
    items,
    confirmed,
    onChange,
}) => {
    const toggle = (key: string, checked: boolean) => {
        onChange(checked
            ? [...confirmed.filter(item => item !== key), key]
            : confirmed.filter(item => item !== key));
    };
    const remaining = items.filter(item => !confirmed.includes(item.key)).length;

    return (
        <Card size="small" title="验收记录">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {items.map(item => (
                    <Checkbox
                        key={item.key}
                        checked={confirmed.includes(item.key)}
                        aria-label={`确认 ${item.key} 验收通过`}
                        onChange={event => toggle(item.key, event.target.checked)}
                    >
                        <Space size="small">
                            <Text>{item.label}</Text>
                            {item.expected && <Text type="secondary">{item.expected}</Text>}
                        </Space>
                    </Checkbox>
                ))}

                <Text type={remaining === 0 ? 'success' : 'warning'}>
                    {remaining === 0 ? '验收完成' : `还有 ${remaining} 项待验收`}
                </Text>
            </Space>
        </Card>
    );
};

export default VerifyChecklistPanel;
