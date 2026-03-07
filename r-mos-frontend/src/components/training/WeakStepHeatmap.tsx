import React, { useMemo, useState } from 'react';
import { Button, Card, Space, Tag } from 'antd';

export interface WeakStepItem {
  stepId: string;
  stepName: string;
  failCount: number;
}

export interface WeakStepHeatmapProps {
  steps: WeakStepItem[];
  onStepSelect?: (stepId: string) => void;
}

type HeatLevel = 'white' | 'light-red' | 'mid-red' | 'deep-red';

function resolveHeatLevel(failCount: number): HeatLevel {
  if (failCount <= 0) {
    return 'white';
  }
  if (failCount <= 2) {
    return 'light-red';
  }
  if (failCount <= 5) {
    return 'mid-red';
  }
  return 'deep-red';
}

function resolveHeatColor(level: HeatLevel): string {
  if (level === 'white') {
    return '#ffffff';
  }
  if (level === 'light-red') {
    return '#ffe5e5';
  }
  if (level === 'mid-red') {
    return '#ffadad';
  }
  return '#ff4d4f';
}

export const WeakStepHeatmap: React.FC<WeakStepHeatmapProps> = ({ steps, onStepSelect }) => {
  const [selected, setSelected] = useState<WeakStepItem | null>(null);
  const data = useMemo(
    () =>
      steps.map((step) => ({
        ...step,
        heat: resolveHeatLevel(step.failCount),
      })),
    [steps]
  );

  return (
    <Card title="薄弱步骤热力图">
      <Space direction="vertical" style={{ width: '100%' }} size={8}>
        {data.map((step) => (
          <Button
            key={step.stepId}
            data-testid={`heat-step-${step.stepId}`}
            data-heat={step.heat}
            style={{
              justifyContent: 'space-between',
              background: resolveHeatColor(step.heat),
              color: step.heat === 'deep-red' ? '#fff' : '#000',
            }}
            onClick={() => {
              setSelected(step);
              onStepSelect?.(step.stepId);
            }}
          >
            <span>{step.stepName}</span>
            <span>{step.failCount}</span>
          </Button>
        ))}
      </Space>

      {selected ? (
        <div style={{ marginTop: 12, padding: 12, border: '1px solid #d9d9d9', borderRadius: 8 }}>
          <h4>步骤详情</h4>
          <p>{selected.stepName}</p>
          <Tag color="red">失败次数: {selected.failCount}</Tag>
        </div>
      ) : null}
    </Card>
  );
};

export default WeakStepHeatmap;
