import React, { useEffect, useState } from 'react';
import { Tag, Typography } from 'antd';
import {
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  LoadingOutlined,
  StopFilled,
} from '@ant-design/icons';

const { Text } = Typography;

export type WorkbenchCapsuleState =
  | 'IDLE'
  | 'EXECUTING'
  | 'NEED_EVIDENCE'
  | 'WAITING_APPROVAL'
  | 'BLOCKED'
  | 'DONE';

export interface WorkbenchCapsulePayload {
  state: WorkbenchCapsuleState;
  title: string;
  detail?: string;
  action?: string;
}

const CAPSULE_STORAGE_KEY = 'rmos_agent_status_capsule';

const iconMap: Record<
  Exclude<WorkbenchCapsuleState, 'IDLE'>,
  { color: string; icon: React.ReactNode; text: string }
> = {
  EXECUTING: { color: 'processing', icon: <LoadingOutlined />, text: '执行中' },
  NEED_EVIDENCE: { color: 'warning', icon: <ExclamationCircleFilled />, text: '需证据' },
  WAITING_APPROVAL: { color: 'gold', icon: <ClockCircleFilled />, text: '等审批' },
  BLOCKED: { color: 'error', icon: <StopFilled />, text: '阻塞' },
  DONE: { color: 'success', icon: <CheckCircleFilled />, text: '已完成' },
};

const AgentStatusCapsule: React.FC = () => {
  const [capsule, setCapsule] = useState<WorkbenchCapsulePayload | null>(null);

  useEffect(() => {
    const refresh = () => {
      try {
        const raw = sessionStorage.getItem(CAPSULE_STORAGE_KEY);
        if (!raw) {
          setCapsule(null);
          return;
        }
        const parsed = JSON.parse(raw) as WorkbenchCapsulePayload;
        if (parsed.state === 'IDLE') {
          setCapsule(null);
          return;
        }
        setCapsule(parsed);
      } catch {
        setCapsule(null);
      }
    };

    refresh();
    window.addEventListener('storage', refresh);
    window.addEventListener('agent-status-updated', refresh as EventListener);

    return () => {
      window.removeEventListener('storage', refresh);
      window.removeEventListener('agent-status-updated', refresh as EventListener);
    };
  }, []);

  if (!capsule || capsule.state === 'IDLE') {
    return null;
  }

  const config = iconMap[capsule.state as Exclude<WorkbenchCapsuleState, 'IDLE'>];

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <Tag
        icon={config.icon}
        color={config.color}
        style={{
          marginInlineEnd: 0,
          borderRadius: 999,
          paddingInline: 10,
          height: 28,
          display: 'flex',
          alignItems: 'center',
          fontWeight: 600,
        }}
      >
        {config.text}
      </Tag>
      <Text style={{ color: '#e8edf4' }}>{capsule.title}</Text>
      {capsule.detail ? <Text style={{ color: '#9fb0c8' }}>{capsule.detail}</Text> : null}
      {capsule.action ? <Text style={{ color: '#8dc5ff' }}>{capsule.action}</Text> : null}
    </div>
  );
};

export const setWorkbenchCapsule = (payload: WorkbenchCapsulePayload | null) => {
  if (!payload || payload.state === 'IDLE') {
    sessionStorage.removeItem(CAPSULE_STORAGE_KEY);
  } else {
    sessionStorage.setItem(CAPSULE_STORAGE_KEY, JSON.stringify(payload));
  }
  window.dispatchEvent(new Event('agent-status-updated'));
};

export default AgentStatusCapsule;
