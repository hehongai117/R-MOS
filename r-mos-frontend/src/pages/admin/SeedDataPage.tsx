/**
 * 种子数据管理页面（V1.2 P0修复版）
 * 
 * ⚠️ P0-3修复说明：
 * - MVP阶段种子数据导入通过SSH命令手动执行，不提供Web界面
 * - 本页面改为"导入说明"，展示SSH命令和执行步骤
 * - 未来版本计划：提供 POST /api/v1/admin/import-seed-data API端点
 */
import React from 'react';
import { Card, Typography, Alert, Divider, Space } from 'antd';
import { CodeOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const SeedDataPage: React.FC = () => {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2}>
        <CodeOutlined /> 种子数据导入说明（SSH手动执行）
      </Title>
      
      <Alert
        message="MVP阶段限制"
        description="当前版本的种子数据导入需要通过SSH命令手动执行，不提供Web界面。完整版将支持一键导入功能。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card title="📦 种子数据内容" style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>✅ 3套Demo SOP：</Text>
            <ul>
              <li>右膝关节维护标准流程（12步）</li>
              <li>手腕关节PID参数调试（8步）</li>
              <li>日常巡检标准流程（6步）</li>
            </ul>
          </div>
          
          <div>
            <Text strong>✅ 5个故障案例：</Text>
            <ul>
              <li>E001_OVERHEAT - 电机过热</li>
              <li>E002_STALL - 电机堵转</li>
              <li>E003_ENCODER_ERROR - 编码器故障</li>
              <li>E004_COMM_TIMEOUT - 通信超时</li>
              <li>E005_OVERLOAD - 过载保护</li>
            </ul>
          </div>
        </Space>
      </Card>

      <Card title="🚀 导入步骤" style={{ marginBottom: 24 }}>
        <Typography>
          <Title level={4}>步骤1：SSH登录到服务器</Title>
          <Paragraph>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              overflow: 'auto'
            }}>
{`ssh user@your-server-ip
cd /path/to/r-mos-backend`}
            </pre>
          </Paragraph>

          <Divider />

          <Title level={4}>步骤2：激活虚拟环境（如有）</Title>
          <Paragraph>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              overflow: 'auto'
            }}>
{`source venv/bin/activate  # Linux/Mac
# 或
venv\\Scripts\\activate  # Windows`}
            </pre>
          </Paragraph>

          <Divider />

          <Title level={4}>步骤3：确保数据库迁移已完成</Title>
          <Paragraph>
            <Alert
              message="⚠️ 重要"
              description="种子数据导入依赖数据库表结构，必须先运行迁移脚本"
              type="warning"
              showIcon
              icon={<WarningOutlined />}
              style={{ marginBottom: 12 }}
            />
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              overflow: 'auto'
            }}>
{`# 创建数据库（如果尚未创建）
createdb rmos_dev

# 运行数据库迁移
alembic upgrade head`}
            </pre>
          </Paragraph>

          <Divider />

          <Title level={4}>步骤4：执行种子数据导入</Title>
          <Paragraph>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              overflow: 'auto'
            }}>
{`python -m scripts.seed_data`}
            </pre>
          </Paragraph>

          <Divider />

          <Title level={4}>步骤5：验证导入结果</Title>
          <Paragraph>
            <Text>预期输出示例：</Text>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              overflow: 'auto',
              color: '#52c41a'
            }}>
{`✅ 已导入SOP: 右膝关节维护标准流程（ID: 1）
✅ 已导入SOP: 手腕关节PID参数调试（ID: 2）
✅ 已导入SOP: 日常巡检标准流程（ID: 3）
✅ 已导入故障案例: E001_OVERHEAT
✅ 已导入故障案例: E002_STALL
✅ 已导入故障案例: E003_ENCODER_ERROR
✅ 已导入故障案例: E004_COMM_TIMEOUT
✅ 已导入故障案例: E005_OVERLOAD
✅ 种子数据导入完成！`}
            </pre>
          </Paragraph>

          <Divider />

          <Title level={4}>步骤6：刷新前端页面</Title>
          <Paragraph>
            导入完成后，刷新SOP列表页面即可看到新导入的数据。
          </Paragraph>
        </Typography>
      </Card>

      <Card title="⚠️ 常见问题" style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong type="danger">❌ ModuleNotFoundError: No module named 'app.services.sop_service'</Text>
            <Paragraph>
              <Text type="secondary">原因：</Text>未安装依赖或未设置PYTHONPATH<br />
              <Text type="secondary">解决：</Text><code>pip install -r requirements.txt</code>
            </Paragraph>
          </div>

          <Divider />

          <div>
            <Text strong type="danger">❌ sqlalchemy.exc.ProgrammingError: relation "sops" does not exist</Text>
            <Paragraph>
              <Text type="secondary">原因：</Text>未运行数据库迁移<br />
              <Text type="secondary">解决：</Text><code>alembic upgrade head</code>
            </Paragraph>
          </div>

          <Divider />

          <div>
            <Text strong type="warning">⚠️ asyncpg.exceptions.UniqueViolationError: duplicate key value</Text>
            <Paragraph>
              <Text type="secondary">原因：</Text>种子数据已导入（重复执行）<br />
              <Text type="secondary">解决：</Text>这是正常现象，可忽略或先清空数据库
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card title="📅 未来版本计划" style={{ marginBottom: 24 }}>
        <Alert
          message="完整版功能预告"
          description={
            <ul>
              <li>✨ 提供 <code>POST /api/v1/admin/import-seed-data</code> API端点</li>
              <li>✨ 支持Web界面一键导入</li>
              <li>✨ 支持导入进度实时显示</li>
              <li>✨ 支持自定义种子数据上传</li>
              <li>✨ 支持导入历史记录查看</li>
            </ul>
          }
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
        />
      </Card>
    </div>
  );
};

export default SeedDataPage;
