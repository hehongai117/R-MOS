import React, { useMemo, useState } from 'react';
import { Card } from 'antd';

export interface TrainingRecord {
  id: string;
  model: string;
  score: number;
  trainedAt: string;
}

export interface TrainingTimelineProps {
  records: TrainingRecord[];
  filterLabel?: string;
}

export const TrainingTimeline: React.FC<TrainingTimelineProps> = ({
  records,
  filterLabel = '机型筛选',
}) => {
  const [selectedModel, setSelectedModel] = useState('ALL');

  const models = useMemo(() => {
    return Array.from(new Set(records.map((record) => record.model)));
  }, [records]);

  const filtered = useMemo(() => {
    if (selectedModel === 'ALL') {
      return records;
    }
    return records.filter((record) => record.model === selectedModel);
  }, [records, selectedModel]);

  return (
    <Card title="训练时间线">
      <div style={{ marginBottom: 12 }}>
        <label htmlFor="timeline-model-filter" style={{ marginRight: 8 }}>
          {filterLabel}
        </label>
        <select
          id="timeline-model-filter"
          value={selectedModel}
          onChange={(event) => setSelectedModel(event.target.value)}
        >
          <option value="ALL">全部</option>
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </div>

      <ul style={{ paddingInlineStart: 18 }}>
        {filtered.map((record) => (
          <li key={record.id} data-testid="timeline-point">
            {record.trainedAt} | {record.model} | {record.score}
          </li>
        ))}
      </ul>
    </Card>
  );
};

export default TrainingTimeline;
