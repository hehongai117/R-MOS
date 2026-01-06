/**
 * Task执行页（V1.2 P0修复版）
 * 
 * P0修复：添加 404 处理，防止用户被困
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Steps, Card, message, Modal, Result, Spin } from 'antd';
import { PlayCircleOutlined, PauseOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { getTask, executeStep, pauseTask, resumeTask } from '@/api/task';
import { TaskWithSOP, StepExecutionResponse } from '@/types/task';
import { SOPStep } from '@/types/sop';

const TaskExecutionPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<TaskWithSOP | null>(null);
  const [steps, setSteps] = useState<SOPStep[]>([]);
  const [loading, setLoading] = useState(true);  // 默认 true，首次加载
  const [executing, setExecuting] = useState(false);
  const [notFound, setNotFound] = useState(false);  // P0修复：404 状态

  useEffect(() => {
    if (taskId) {
      loadTask(parseInt(taskId));
    } else {
      // 无 taskId 参数
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
      // 安全访问 sop.steps
      if (taskData.sop?.steps) {
        setSteps(taskData.sop.steps as SOPStep[]);
      }
    } catch (error: any) {
      // P0修复：区分 404 和其他错误
      if (error.response?.status === 404) {
        setNotFound(true);
        message.error('任务不存在');
      } else {
        message.error('加载任务失败');
        setNotFound(true);  // 也标记为找不到，显示返回按钮
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

      // ✅ V1.1修复：使用is_task_completed判断任务是否完成
      if (response.is_task_completed) {
        // 任务完成，弹出评分对话框
        Modal.success({
          title: '任务完成！',
          content: `您的最终得分：${task.final_score || '计算中...'}`,
          onOk: () => navigate(`/reports/${task.id}`),
        });
      } else {
        // 刷新任务状态
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

  // P0修复：加载中状态
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>加载任务中...</p>
      </div>
    );
  }

  // P0修复：任务不存在状态
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
      <Card title={task.title}>
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
              <Button
                icon={<PauseOutlined />}
                onClick={handlePause}
                style={{ marginLeft: 8 }}
              >
                暂停
              </Button>
            </>
          )}

          {task.status === 'paused' && (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleResume}
            >
              继续执行
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
};

export default TaskExecutionPage;
