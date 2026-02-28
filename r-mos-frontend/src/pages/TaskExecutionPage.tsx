/**
 * Task执行页（V1.2 P0修复版 + P0增强版）
 *
 * P0增强：集成 TaskControl 和 EvidencePanel 组件
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Steps, Card, message, Modal, Result, Spin, Row, Col, Divider } from 'antd';
import { PlayCircleOutlined, PauseOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { getTask, executeStep, pauseTask, resumeTask } from '@/api/task';
import { TaskWithSOP, StepExecutionResponse } from '@/types/task';
import { SOPStep } from '@/types/sop';
import { TaskControl } from '@/components/TaskControl';
import { EvidencePanel } from '@/components/EvidencePanel';

const TaskExecutionPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<TaskWithSOP | null>(null);
  const [steps, setSteps] = useState<SOPStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [notFound, setNotFound] = useState(false);

  // Evidence state (mock for now - will integrate with API)
  const [evidenceStatus, setEvidenceStatus] = useState({
    required: [
      { id: 'ev-1', type: 'trajectory' as const, status: 'collected' as const },
      { id: 'ev-2', type: 'screenshot' as const, status: 'required' as const },
    ],
    collected: [
      { id: 'ev-1', type: 'trajectory' as const, status: 'collected' as const },
    ],
  });

  useEffect(() => {
    if (taskId) {
      loadTask(parseInt(taskId));
    } else {
      setNotFound(true);
      setLoading(false);
    }
  }, [taskId]);

  const loadTask = async (id: number) => {
    setLoading(true);
    setNotFound(false);
    try {
      const taskData = await getTask(id) as TaskWithSOP;
      setTask(taskData);
      if (taskData.sop?.steps) {
        setSteps(taskData.sop.steps as SOPStep[]);
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        setNotFound(true);
        message.error('任务不存在');
      } else {
        message.error('加载任务失败');
        setNotFound(true);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteStep = async (stepIndex: number) => {
    if (!task) return;

    setExecuting(true);
    try {
      const response: StepExecutionResponse = await executeStep(task.id, {
        step_index: stepIndex,
        action: 'execute',
        parameters: {},
      });

      message.success(response.message);

      if (response.is_task_completed) {
        Modal.success({
          title: '任务完成！',
          content: `您的最终得分：${task.final_score || '计算中...'}`,
          onOk: () => navigate(`/reports/${task.id}`),
        });
      } else {
        await loadTask(task.id);
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '步骤执行失败');
    } finally {
      setExecuting(false);
    }
  };

  const handlePause = async () => {
    if (!task) return;
    try {
      await pauseTask(task.id);
      message.success('任务已暂停');
      await loadTask(task.id);
    } catch (error) {
      message.error('暂停失败');
    }
  };

  const handleResume = async () => {
    if (!task) return;
    try {
      await resumeTask(task.id);
      message.success('任务已恢复');
      await loadTask(task.id);
    } catch (error) {
      message.error('恢复失败');
    }
  };

  const handleHelp = () => {
    // TODO: Integrate with Coach Agent API
    message.info('正在连接教练Agent...');
  };

  // Mock next action from Coach Agent
  const nextAction = {
    actionType: 'select_tool',
    target: 'screwdriver',
    explanation: '请选择合适的螺丝刀工具',
  };

  // Mock permissions (should come from backend RBAC)
  const permissions = {
    canStart: task?.status === 'ready',
    canPause: task?.status === 'in_progress',
    canResume: task?.status === 'paused',
    canSkip: false,
    canRollback: false,
    canAbort: true,
    canForceContinue: false,
  };

  // Map task status to FSM state
  const getFSMStatus = () => {
    if (!task) return 'READY';
    const statusMap: Record<string, string> = {
      'pending': 'READY',
      'in_progress': 'EXECUTING',
      'paused': 'PAUSED',
      'completed': 'COMPLETED',
      'failed': 'FAILED',
    };
    return statusMap[task.status] || 'READY';
  };

  // Loading state
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>加载任务中...</p>
      </div>
    );
  }

  // Not found state
  if (notFound || !task) {
    return (
      <Result
        status="404"
        title="任务不存在"
        subTitle="您访问的任务可能已被删除或从未创建。"
        extra={
          <Button
            type="primary"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/sops')}
          >
            返回 SOP 列表
          </Button>
        }
      />
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        {/* Left Column - Task Control */}
        <Col xs={24} lg={16}>
          {/* TaskControl Component */}
          <TaskControl
            taskName={task.title}
            taskId={String(task.id)}
            riskLevel="R1"
            status={getFSMStatus() as any}
            currentStep={task.current_step_index + 1}
            totalSteps={steps.length}
            nextAction={nextAction}
            canStart={permissions.canStart}
            canPause={permissions.canPause}
            canResume={permissions.canResume}
            canSkip={permissions.canSkip}
            canRollback={permissions.canRollback}
            canAbort={permissions.canAbort}
            canForceContinue={permissions.canForceContinue}
            onStart={() => handleExecuteStep(0)}
            onPause={handlePause}
            onResume={handleResume}
            onHelp={handleHelp}
          />

          {/* Steps Display */}
          <Card title="任务步骤" style={{ marginTop: 16 }}>
            <Steps
              current={task.current_step_index}
              items={steps.map((step) => ({
                title: step.title,
                description: step.description,
              }))}
            />

            <div style={{ marginTop: 24 }}>
              {task.status === 'in_progress' && (
                <>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={executing}
                    onClick={() => handleExecuteStep(task.current_step_index + 1)}
                    disabled={task.current_step_index >= steps.length}
                  >
                    执行下一步
                  </Button>
                </>
              )}
            </div>
          </Card>

          {/* Current Step Details */}
          {steps[task.current_step_index] && (
            <Card title="当前步骤" style={{ marginTop: 16 }}>
              <h3>{steps[task.current_step_index].title}</h3>
              <p>{steps[task.current_step_index].description}</p>
            </Card>
          )}
        </Col>

        {/* Right Column - Evidence Panel */}
        <Col xs={24} lg={8}>
          <EvidencePanel
            stepId={`step-${task.current_step_index}`}
            stepName={steps[task.current_step_index]?.title || '当前步骤'}
            requiredEvidence={evidenceStatus.required}
            collectedEvidence={evidenceStatus.collected}
            canProceed={evidenceStatus.collected.length > 0}
            missingEvidenceCount={evidenceStatus.required.length - evidenceStatus.collected.length}
          />
        </Col>
      </Row>
    </div>
  );
};

export default TaskExecutionPage;
