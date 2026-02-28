// Permission Hint Component
// P2: Show user permissions and locked actions

import React from 'react';
import { Tag, Tooltip, Space } from 'antd';
import { LockOutlined, UnlockOutlined, UserOutlined } from '@ant-design/icons';

interface PermissionHintProps {
  // Current user role
  userRole: 'trainee' | 'engineer' | 'instructor' | 'system';

  // Action that user is trying to perform
  attemptedAction?: string;

  // Custom messages
  messages?: {
    locked?: string;
    unlocked?: string;
  };
}

// Permission matrix
const PERMISSIONS = {
  trainee: {
    start_task: true,
    pause_task: true,
    skip_step: false,
    force_continue: false,
    rollback_task: false,
    abort_task: true,
    approve_knowledge: false,
    view_all_reports: false,
  },
  engineer: {
    start_task: true,
    pause_task: true,
    skip_step: true,
    force_continue: true,
    rollback_task: false,
    abort_task: true,
    approve_knowledge: false,
    view_all_reports: false,
  },
  instructor: {
    start_task: true,
    pause_task: true,
    skip_step: true,
    force_continue: true,
    rollback_task: true,
    abort_task: true,
    approve_knowledge: true,
    view_all_reports: true,
  },
  system: {
    start_task: true,
    pause_task: true,
    skip_step: true,
    force_continue: true,
    rollback_task: true,
    abort_task: true,
    approve_knowledge: true,
    view_all_reports: true,
  },
};

const roleLabels = {
  trainee: '学员',
  engineer: '工程师',
  instructor: '教员',
  system: '系统',
};

const roleColors = {
  trainee: 'blue',
  engineer: 'green',
  instructor: 'red',
  system: 'purple',
};

const actionLabels: Record<string, string> = {
  start_task: '开始任务',
  pause_task: '暂停任务',
  skip_step: '跳过步骤',
  force_continue: '强制继续',
  rollback_task: '回滚任务',
  abort_task: '中止任务',
  approve_knowledge: '审核知识',
  view_all_reports: '查看所有报告',
};

export const PermissionHint: React.FC<PermissionHintProps> = ({
  userRole,
  attemptedAction,
  messages = {},
}) => {
  const permissions = PERMISSIONS[userRole];

  // If user is trying to perform an action
  if (attemptedAction && permissions[attemptedAction as keyof typeof permissions] === false) {
    return (
      <Tooltip title={messages.locked || `需要更高权限才能执行此操作`}>
        <Tag color="red" icon={<LockOutlined />}>
          {actionLabels[attemptedAction] || attemptedAction} (无权限)
        </Tag>
      </Tooltip>
    );
  }

  // Show current role and permissions summary
  return (
    <Space direction="vertical" size="small">
      {/* Current Role */}
      <Space>
        <UserOutlined />
        <Tag color={roleColors[userRole]}>
          {roleLabels[userRole]}
        </Tag>
      </Space>

      {/* Quick Permission Check */}
      {attemptedAction && (
        <div>
          {permissions[attemptedAction as keyof typeof permissions] ? (
            <Tag color="green" icon={<UnlockOutlined />}>
              {messages.unlocked || '可执行'}
            </Tag>
          ) : (
            <Tag color="red" icon={<LockOutlined />}>
              {messages.locked || '无权限'}
            </Tag>
          )}
        </div>
      )}
    </Space>
  );
};

// Hook for checking permissions
export const usePermission = (userRole: 'trainee' | 'engineer' | 'instructor' | 'system') => {
  const hasPermission = (action: string): boolean => {
    return PERMISSIONS[userRole][action as keyof typeof PERMISSIONS.trainee] || false;
  };

  const canPerform = (...actions: string[]): boolean => {
    return actions.some((action) => hasPermission(action));
  };

  return {
    hasPermission,
    canPerform,
    role: userRole,
  };
};

export default PermissionHint;
