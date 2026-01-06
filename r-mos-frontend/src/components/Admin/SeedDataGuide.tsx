/**
 * 种子数据导入说明组件（可在多处复用）
 */
import React from 'react';
import { Alert, Typography, Space } from 'antd';
import { CodeOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

export const SeedDataGuide: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Alert
        message="种子数据导入说明"
        description="MVP阶段需要通过SSH手动执行，请参考管理页面的详细说明"
        type="info"
        showIcon
        icon={<CodeOutlined />}
      />
      
      <div>
        <Text strong>快速导入命令：</Text>
        <Paragraph>
          <pre style={{ 
            background: '#f5f5f5', 
            padding: '8px', 
            borderRadius: '4px',
            fontSize: '12px'
          }}>
{`# 1. SSH登录服务器
ssh user@your-server-ip

# 2. 进入项目目录
cd /path/to/r-mos-backend

# 3. 运行迁移（如果尚未运行）
alembic upgrade head

# 4. 导入种子数据
python -m scripts.seed_data`}
          </pre>
        </Paragraph>
      </div>
    </Space>
  );
};
