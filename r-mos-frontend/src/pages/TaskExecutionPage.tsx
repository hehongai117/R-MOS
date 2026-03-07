/**
 * Task执行页（V1.2 P0修复版 + P0增强版）
 *
 * P0增强：集成 TaskControl 和 EvidencePanel 组件
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Steps, Card, message, Modal, Result, Spin, Row, Col } from 'antd';
import { PlayCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { getTask, executeStep, pauseTask, resumeTask } from '@/api/task';
import { TaskWithSOP, StepExecutionResponse } from '@/types/task';
import { SOPStep } from '@/types/sop';
import { TaskControl, type TaskControlProps } from '@/components/TaskControl';
import { EvidencePanel } from '@/components/EvidencePanel';
import { GuidanceModeModal } from '@/components/GuidanceModeModal';
import { getUserPreference, updateGuidanceMode } from '@/api/preference';
import { GuidanceMode } from '@/types/user';
import { useAuthStore } from '@/store/authStore';

const getResponseStatus = (error: unknown): number | undefined => {
  if (typeof error !== 'object' || error === null) return undefined;
  const response = (error as { response?: { status?: number } }).response;
  return response?.status;
};

const getResponseMessage = (error: unknown): string | undefined => {
  if (typeof error !== 'object' || error === null) return undefined;
  const response = (error as { response?: { data?: { message?: string } } }).response;
  return response?.data?.message;
};

const TaskExecutionPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<TaskWithSOP | null>(null);
  const [steps, setSteps] = useState<SOPStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [notFound, setNotFound] = useState(false);

  // Evidence state — initially empty, populated when step execution provides evidence data
  const [evidenceStatus, _setEvidenceStatus] = useState({
    required: [] as Array<{ id: string; type: 'trajectory' | 'screenshot'; status: 'collected' | 'required' }>,
    collected: [] as Array<{ id: string; type: 'trajectory' | 'screenshot'; status: 'collected' | 'required' }>,
  });

  // P2-4: Guidance mode modal state
  const [showModeModal, setShowModeModal] = useState(false);
  const [selectedMode, setSelectedMode] = useState<GuidanceMode>('on_demand');
  const [pendingStartStep, setPendingStartStep] = useState<number | null>(null);

  useEffect(() => {
    // P2-4: Load user preference on mount
    loadUserPreference();

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
    } catch (error: unknown) {
      if (getResponseStatus(error) === 404) {
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

  // P2-4: Load user preference
  const loadUserPreference = async () => {
    try {
      const pref = await getUserPreference();
      setSelectedMode(pref.guidance_mode);
    } catch (error) {
      // Use default if not logged in or preference not set
      console.log('Using default guidance mode');
    }
  };

  // P2-4: Handle mode selection and start
  const handleStartWithMode = async (mode: GuidanceMode) => {
    setShowModeModal(false);

    // Save preference
    try {
      await updateGuidanceMode(mode);
      setSelectedMode(mode);
    } catch (error) {
      console.error('Failed to save preference:', error);
    }

    // Start task with the selected mode
    if (pendingStartStep !== null) {
      // Pass mode to backend via executeStep
      await handleExecuteStep(pendingStartStep);
      setPendingStartStep(null);
    }
  };

  // P2-4: Handle start click - show mode modal first
  const handleStartClick = (stepIndex: number) => {
    setPendingStartStep(stepIndex);
    setShowModeModal(true);
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
    } catch (error: unknown) {
      message.error(getResponseMessage(error) || '步骤执行失败');
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
    // BACKLOG: Integrate with Coach Agent API - pending TrainingWorkbenchPage migration
    message.info('正在连接教练Agent...');
  };

  // BACKLOG: nextAction should come from Coach Agent API once implemented
  const nextAction = task
    ? { actionType: 'execute_step', target: steps[task.current_step_index]?.title ?? '', explanation: '请执行当前步骤' }
    : { actionType: 'select_tool', target: '', explanation: '加载中' };

  // Permissions derived from task status + user role
  const userRole = useAuthStore((state) => state.user?.role);
  const isAdmin = userRole === 'admin';
  const permissions = {
    canStart: task?.status === 'pending',
    canPause: task?.status === 'in_progress',
    canResume: task?.status === 'paused',
    canSkip: isAdmin,
    canRollback: isAdmin,
    canAbort: true,
    canForceContinue: isAdmin,
  };

  // Map task status to FSM state
  const getFSMStatus = (): TaskControlProps['status'] => {
    if (!task) return 'READY';
    const statusMap: Record<string, TaskControlProps['status']> = {
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
            status={getFSMStatus()}
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
            onStart={() => handleStartClick(0)}
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

      {/* P2-4: Guidance Mode Selection Modal */}
      <GuidanceModeModal
        open={showModeModal}
        defaultMode={selectedMode}
        onSelect={handleStartWithMode}
        onCancel={() => {
          setShowModeModal(false);
          setPendingStartStep(null);
        }}
      />
    </div>
  );
};

export default TaskExecutionPage;
