// TaskControl Panel Component
// Phase 6: Guardrail UI - Task Control

import React from 'react';
import { Button, Card, Tag, Space, Tooltip, Badge } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  RollbackOutlined,
  StopOutlined,
  QuestionCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

interface TaskControlProps {
  // Task info
  taskName: string;
  taskId: string;
  riskLevel: 'R0' | 'R1' | 'R2' | 'R3';
  status: 'READY' | 'EXECUTING' | 'PAUSED' | 'WAITING_CONFIRM' | 'FAILED' | 'COMPLETED' | 'ABORTED';
  currentStep: number;
  totalSteps: number;

  // Next action suggestion
  nextAction?: {
    actionType: string;
    target: string;
    explanation: string;
  };

  // Permissions
  canStart: boolean;
  canPause: boolean;
  canResume: boolean;
  canSkip: boolean;
  canRollback: boolean;
  canAbort: boolean;
  canForceContinue: boolean;

  // Handlers
  onStart?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onSkip?: () => void;
  onRollback?: () => void;
  onAbort?: () => void;
  onForceContinue?: () => void;
  onHelp?: () => void;
}

const riskColors: Record<string, string> = {
  R0: 'green',
  R1: 'blue',
  R2: 'orange',
  R3: 'red',
};

const statusColors: Record<string, string> = {
  READY: 'blue',
  EXECUTING: 'processing',
  PAUSED: 'warning',
  WAITING_CONFIRM: 'orange',
  FAILED: 'error',
  COMPLETED: 'success',
  ABORTED: 'default',
};

export const TaskControl: React.FC<TaskControlProps> = ({
  taskName,
  taskId,
  riskLevel,
  status,
  currentStep,
  totalSteps,
  nextAction,
  canStart,
  canPause,
  canResume,
  canSkip,
  canRollback,
  canAbort,
  canForceContinue,
  onStart,
  onPause,
  onResume,
  onSkip,
  onRollback,
  onAbort,
  onForceContinue,
  onHelp,
}) => {
  const isExecuting = status === 'EXECUTING';
  const isPaused = status === 'PAUSED';
  const isWaitingConfirm = status === 'WAITING_CONFIRM';

  return (
    <Card
      title={
        <Space>
          <span>{taskName}</span>
          <Tag color={riskColors[riskLevel]}>{riskLevel}</Tag>
        </Space>
      }
      extra={
        <Badge status={statusColors[status] as any} text={status} />
      }
      style={{ marginBottom: 16 }}
    >
      {/* Progress */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <span>步骤: {currentStep} / {totalSteps}</span>
          <ProgressBar current={currentStep} total={totalSteps} />
        </Space>
      </div>

      {/* Next Action Suggestion */}
      {nextAction && isExecuting && (
        <Card size="small" style={{ marginBottom: 16, background: '#f5f5f5' }}>
          <div>
            <strong>建议操作:</strong> {nextAction.actionType}
            {nextAction.target && <span> - {nextAction.target}</span>}
          </div>
          {nextAction.explanation && (
            <div style={{ color: '#666', marginTop: 4 }}>
              {nextAction.explanation}
            </div>
          )}
        </Card>
      )}

      {/* Control Buttons */}
      <Space wrap>
        {/* Start */}
        {status === 'READY' && canStart && (
          <Tooltip title="开始任务">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={onStart}
            >
              开始
            </Button>
          </Tooltip>
        )}

        {/* Pause */}
        {isExecuting && canPause && (
          <Tooltip title="暂停任务">
            <Button
              icon={<PauseCircleOutlined />}
              onClick={onPause}
            >
              暂停
            </Button>
          </Tooltip>
        )}

        {/* Resume */}
        {isPaused && canResume && (
          <Tooltip title="恢复任务">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={onResume}
            >
              继续
            </Button>
          </Tooltip>
        )}

        {/* Skip Step */}
        {isExecuting && canSkip<Tooltip title="跳过 && (
          当前步骤">
            <Button
              icon={<CheckCircleOutlined />}
              onClick={onSkip}
            >
              跳过
            </Button>
          </Tooltip>
        )}

        {/* Force Continue (Instructor only) */}
        {isWaitingConfirm && canForceContinue && (
          <Tooltip title="强制继续 (需教员权限)">
            <Button
              danger
              icon={<QuestionCircleOutlined />}
              onClick={onForceContinue}
            >
              强制继续
            </Button>
          </Tooltip>
        )}

        {/* Rollback (Instructor only) */}
        {canRollback && (
          <Tooltip title="回滚任务 (需教员权限)">
            <Button
              icon={<RollbackOutlined />}
              onClick={onRollback}
            >
              回滚
            </Button>
          </Tooltip>
        )}

        {/* Abort */}
        {canAbort && status !== 'COMPLETED' && status !== 'ABORTED' && (
          <Tooltip title="中止任务">
            <Button
              danger
              icon={<StopOutlined />}
              onClick={onAbort}
            >
              中止
            </Button>
          </Tooltip>
        )}

        {/* Help */}
        {(isExecuting || isPaused) && (
          <Tooltip title="请求帮助">
            <Button
              icon={<QuestionCircleOutlined />}
              onClick={onHelp}
            >
              求助
            </Button>
          </Tooltip>
        )}
      </Space>
    </Card>
  );
};

// Simple progress bar component
const ProgressBar: React.FC<{ current: number; total: number }> = ({ current, total }) => {
  const percent = total > 0 ? (current / total) * 100 : 0;

  return (
    <div style={{ width: 200, height: 8, background: '#f0f0f0', borderRadius: 4 }}>
      <div
        style={{
          width: `${percent}%`,
          height: '100%',
          background: '#1890ff',
          borderRadius: 4,
          transition: 'width 0.3s',
        }}
      />
    </div>
  );
};

export default TaskControl;
