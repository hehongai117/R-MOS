/**
 * 步骤卡片组件（V1.1修复版）
 */
import React from 'react';
import { Card, Button, Tag, Space } from 'antd';
import { PlayCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { SOPStep } from '@/types/sop';

interface StepCardProps {
  step: SOPStep;
  currentStepIndex: number;
  onExecute: (stepIndex: number) => void;
  executing: boolean;
}

const StepCard: React.FC<StepCardProps> = ({
  step,
  currentStepIndex,
  onExecute,
  executing
}) => {
  const stepIndex = step.step_index;
  const isActive = stepIndex === currentStepIndex + 1;
  const isCompleted = stepIndex <= currentStepIndex;

  return (
    <Card
      style={{
        marginBottom: 16,
        borderColor: isActive ? '#1890ff' : undefined,
        background: isCompleted ? '#f6ffed' : undefined,
      }}
      extra={
        isCompleted ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            已完成
          </Tag>
        ) : isActive ? (
          <Tag color="processing">进行中</Tag>
        ) : (
          <Tag>待执行</Tag>
        )
      }
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <strong>步骤 {stepIndex}:</strong> {step.title}
        </div>
        <div>{step.description}</div>

        {step.is_critical && (
          <Tag color="red">关键步骤</Tag>
        )}

        {isActive && (
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => onExecute(stepIndex)}
            loading={executing}
          >
            执行此步骤
          </Button>
        )}
      </Space>
    </Card>
  );
};

export default StepCard;
