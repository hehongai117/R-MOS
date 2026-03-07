// EvidencePanel Component
// Phase 6: Guardrail UI - Evidence Panel

import React from 'react';
import { Card, Tag, List, Badge, Space, Tooltip, Progress } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from '@ant-design/icons';

export interface EvidenceItem {
  id: string;
  type: 'trajectory' | 'sensor_reading' | 'screenshot' | 'verdict' | 'timing' | 'state_snapshot';
  status: 'required' | 'collected' | 'missing';
  description?: string;
}

export interface EvidencePanelProps {
  // Step info
  stepId: string;
  stepName: string;

  // Evidence requirements
  requiredEvidence: EvidenceItem[];
  collectedEvidence: EvidenceItem[];

  // Blockers
  canProceed: boolean;
  missingEvidenceCount: number;

  // Evidence refs for diagnosis
  evidenceRefs?: string[];
}

const evidenceTypeLabels: Record<string, string> = {
  trajectory: '轨迹',
  sensor_reading: '传感器',
  screenshot: '截图',
  verdict: '判定',
  timing: '计时',
  state_snapshot: '状态快照',
};

const evidenceTypeColors: Record<string, string> = {
  trajectory: 'blue',
  sensor_reading: 'cyan',
  screenshot: 'purple',
  verdict: 'green',
  timing: 'orange',
  state_snapshot: 'geekblue',
};

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  stepId,
  stepName,
  requiredEvidence,
  collectedEvidence,
  canProceed,
  missingEvidenceCount,
  evidenceRefs = [],
}) => {
  // Merge and deduplicate evidence
  const allEvidence = new Map<string, EvidenceItem>();

  // Add required evidence
  requiredEvidence.forEach((ev) => {
    allEvidence.set(ev.id, ev);
  });

  // Add collected evidence (may override required)
  collectedEvidence.forEach((ev) => {
    allEvidence.set(ev.id, { ...ev, status: 'collected' });
  });

  const evidenceList = Array.from(allEvidence.values());

  // Calculate progress
  const collected = evidenceList.filter((ev) => ev.status === 'collected').length;
  const total = evidenceList.length;
  const progress = total > 0 ? (collected / total) * 100 : 0;

  return (
    <Card
      title={
        <Space>
          <span>证据面板</span>
          <Badge
            count={missingEvidenceCount}
            style={{ backgroundColor: missingEvidenceCount > 0 ? '#ff4d4f' : '#52c41a' }}
          />
        </Space>
      }
      extra={
        <Tag color={canProceed ? 'success' : 'error'}>
          {canProceed ? '可继续' : '缺少证据'}
        </Tag>
      }
      style={{ marginBottom: 16 }}
    >
      {/* Step info */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <span style={{ color: '#666' }}>当前步骤:</span>
          <strong>{stepName}</strong>
          <Tag>{stepId}</Tag>
        </Space>
      </div>

      {/* Progress */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span>证据收集进度</span>
          <span>{collected} / {total}</span>
        </div>
        <Progress
          percent={progress}
          status={canProceed ? 'success' : 'exception'}
          showInfo={false}
        />
      </div>

      {/* Evidence list */}
      <List
        size="small"
        bordered
        dataSource={evidenceList}
        renderItem={(item) => (
          <List.Item>
            <Space>
              {/* Status icon */}
              {item.status === 'collected' ? (
                <Tooltip title="已收集">
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                </Tooltip>
              ) : item.status === 'required' ? (
                <Tooltip title="待收集">
                  <LoadingOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              ) : (
                <Tooltip title="缺失">
                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                </Tooltip>
              )}

              {/* Evidence type */}
              <Tag color={evidenceTypeColors[item.type]}>
                {evidenceTypeLabels[item.type] || item.type}
              </Tag>

              {/* Evidence ID */}
              <span style={{ fontFamily: 'monospace' }}>{item.id}</span>

              {/* Description */}
              {item.description && (
                <span style={{ color: '#666' }}>- {item.description}</span>
              )}
            </Space>
          </List.Item>
        )}
      />

      {/* Evidence refs (for diagnosis) */}
      {evidenceRefs.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 8, color: '#666' }}>诊断引用:</div>
          <Space wrap>
            {evidenceRefs.map((ref) => (
              <Tag key={ref} color="blue">
                {ref}
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* Warning if cannot proceed */}
      {!canProceed && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: 4,
          }}
        >
          <strong style={{ color: '#ff4d4f' }}>无法继续:</strong>
          <span> 需要收集 {missingEvidenceCount} 项证据后才能继续执行任务</span>
        </div>
      )}
    </Card>
  );
};

export default EvidencePanel;
