import React from 'react';
import { Card, Progress, Space } from 'antd';

export interface SkillRadarProfile {
  safety: number;
  quality: number;
  efficiency: number;
  diagnosis: number;
  collaboration: number;
}

export interface SkillRadarChartProps {
  profile: SkillRadarProfile;
}

const labels: Record<keyof SkillRadarProfile, string> = {
  safety: '安全',
  quality: '质量',
  efficiency: '效率',
  diagnosis: '诊断',
  collaboration: '协作',
};

export const SkillRadarChart: React.FC<SkillRadarChartProps> = ({ profile }) => {
  const entries = Object.entries(profile) as Array<[keyof SkillRadarProfile, number]>;

  return (
    <Card title="技能雷达">
      <Space direction="vertical" style={{ width: '100%' }}>
        {entries.map(([key, value]) => (
          <div key={key} data-testid={`radar-item-${key}`}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>{labels[key]}</span>
              <strong>{value}</strong>
            </div>
            <Progress percent={value} showInfo={false} />
          </div>
        ))}
      </Space>
    </Card>
  );
};

export default SkillRadarChart;
