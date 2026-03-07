/**
 * P2-4: Guidance Mode Selection Modal
 * AI 指导模式选择弹窗
 */
import React from 'react';
import { Modal, Typography, Space, Card } from 'antd';
import { BulbOutlined, SoundOutlined, AudioMutedOutlined } from '@ant-design/icons';
import { GuidanceMode } from '@/types/user';

const { Text } = Typography;

interface GuidanceModeModalProps {
  open: boolean;
  onSelect: (mode: GuidanceMode) => void;
  onCancel?: () => void;
  defaultMode?: GuidanceMode;
}

const guidanceModes = [
  {
    value: 'full_time' as GuidanceMode,
    title: '全程指导',
    icon: <BulbOutlined style={{ fontSize: 32, color: '#faad14' }} />,
    description: 'AI 会在每个步骤主动提供指导和建议',
  },
  {
    value: 'on_demand' as GuidanceMode,
    title: '按需指导',
    icon: <SoundOutlined style={{ fontSize: 32, color: '#1890ff' }} />,
    description: 'AI 只在您请求时提供指导',
  },
  {
    value: 'silent' as GuidanceMode,
    title: '静默模式',
    icon: <AudioMutedOutlined style={{ fontSize: 32, color: '#8c8c8c' }} />,
    description: 'AI 不主动提供指导，仅在错误时提醒',
  },
];

export const GuidanceModeModal: React.FC<GuidanceModeModalProps> = ({
  open,
  onSelect,
  onCancel,
  defaultMode = 'on_demand',
}) => {
  const [selectedMode, setSelectedMode] = React.useState<GuidanceMode>(defaultMode);

  const handleOk = () => {
    onSelect(selectedMode);
  };

  return (
    <Modal
      title="选择 AI 指导模式"
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      okText="确认"
      cancelText="取消"
      width={500}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%', marginTop: 16 }}>
        {guidanceModes.map((mode) => (
          <Card
            key={mode.value}
            size="small"
            hoverable
            onClick={() => setSelectedMode(mode.value)}
            style={{
              borderColor: selectedMode === mode.value ? '#1890ff' : '#d9d9d9',
              backgroundColor: selectedMode === mode.value ? '#f0f7ff' : '#fff',
            }}
          >
            <Space>
              {mode.icon}
              <div>
                <Text strong>{mode.title}</Text>
                <br />
                <Text type="secondary">{mode.description}</Text>
              </div>
            </Space>
          </Card>
        ))}
      </Space>
    </Modal>
  );
};

export default GuidanceModeModal;
