import React from 'react';
import { CheckCircleOutlined, LockOutlined } from '@ant-design/icons';
import { Progress, Space, Typography } from 'antd';
import type { SOPPhase } from '@/adjudication';

const { Text } = Typography;

const phaseLabels: Record<SOPPhase, string> = {
    prep: '准备',
    execute: '执行',
    verify: '验证',
};

export interface PhaseProgressItem {
    phase: SOPPhase;
    total: number;
    completed: number;
    unlocked: boolean;
}

interface PhaseProgressProps {
    progress: PhaseProgressItem[];
    currentPhase: SOPPhase | null;
}

export const PhaseProgress: React.FC<PhaseProgressProps> = ({ progress, currentPhase }) => {
    if (progress.length <= 1) return null;

    return (
        <Space style={{ width: '100%', display: 'flex' }} size="small">
            {progress.map(item => {
                const label = phaseLabels[item.phase];
                const complete = item.completed === item.total;
                const active = item.phase === currentPhase;
                const color = item.unlocked ? (complete ? '#52c41a' : '#1890ff') : '#8c8c8c';

                return (
                    <div
                        key={item.phase}
                        aria-label={!item.unlocked ? `${label} 阶段未解锁` : undefined}
                        style={{
                            flex: 1,
                            padding: '6px 8px',
                            border: `1px solid ${active ? '#1890ff' : 'transparent'}`,
                            borderRadius: 4,
                            opacity: item.unlocked ? 1 : 0.55,
                        }}
                    >
                        <Space size={4}>
                            {complete && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                            {!item.unlocked && <LockOutlined />}
                            <Text strong={active} style={{ color }}>{label}</Text>
                            <Text type="secondary">{item.completed}/{item.total}</Text>
                        </Space>
                        <Progress
                            percent={Math.round((item.completed / item.total) * 100)}
                            showInfo={false}
                            size="small"
                            strokeColor={color}
                        />
                    </div>
                );
            })}
        </Space>
    );
};
