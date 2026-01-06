# 📄 修复文件2：rmos拆包D_v1.2.md（P0修复版）

**正在生成完整文件...**

***

```markdown
# R-MOS 拆包D：前端实现（V1.2 P0修复版）

**任务版本：** V1.2（P0修复版）  
**适用范围：** React前端完整实现  
**依赖拆包：** A（Core骨架）、B（业务逻辑）、C（SOP管理）  
**交付目标：** 一个**完整可用的Web前端**，支持SOP执行、实时状态监控、3D可视化与报告查看。

> ⚠️ 本文档为**工程强约束文档**。  
> 外包团队 / 工程师 **不得自行发挥、删减或调整架构与接口语义**。  
> 所有实现必须严格遵循本文档。

**版本历史:**
- V1.0 (2025-12-29): 初始版本
- V1.1 (2025-12-30): P0修复版，路径规范+交互流程修复
- V1.2 (2025-12-30): P0修复版，修正种子数据管理为SSH命令说明

**修复记录（V1.2）:**
- ✅ P0-3: 修正种子数据管理页面，改为SSH命令手动执行说明
- ✅ TL-P0-01: WebSocket路径修正为 `/ws/robot/status`（V1.1已修复）
- ✅ TL-P0-02: 所有HTTP API添加 `/api/v1/` 前缀（V1.1已修复）

***

## 目录

- 1. 技术栈强制要求
- 2. 工程目录结构
- 3. API通信规范（V1.1修复版）
  - 3.1 HTTP API路径规范
  - 3.2 WebSocket连接规范
  - 3.3 错误处理规范
- 4. 核心页面实现
  - 4.1 SOP列表页
  - 4.2 Task执行页
  - 4.3 实时监控面板
  - 4.4 报告页面
- 5. 管理功能页面（V1.2修复版）
  - 5.1 故障案例管理
  - 5.2 种子数据管理（✅ P0-3修复）
- 6. 关键组件实现
  - 6.1 WebSocket Hook
  - 6.2 API Service层
  - 6.3 步骤执行组件
- 7. 3D可视化实现
- 8. 状态管理
- 9. 验收标准
- 10. 交付清单

***

## 1. 技术栈强制要求

| 维度 | 选型要求 | 版本要求 | 备注 |
|---|---|---|---|
| 框架 | **React** | 18+ | 必须使用函数式组件+Hooks |
| 语言 | **TypeScript** | 5+ | 必须启用严格模式 |
| 状态管理 | **Zustand** 或 Redux Toolkit | - | 推荐Zustand（更轻量） |
| UI组件库 | **Ant Design** | 5+ | 保持视觉一致性 |
| HTTP客户端 | **Axios** | - | 统一封装API Service |
| WebSocket | **原生WebSocket API** | - | 封装自定义Hook |
| 3D渲染 | **Three.js** + React-Three-Fiber | - | 仅用于机器人可视化 |
| 路由 | **React Router** | 6+ | 使用Data Router模式 |
| 构建工具 | **Vite** | - | 比Create React App更快 |

***

## 2. 工程目录结构

```
/r-mos-frontend
├── /src
│   ├── /api                    # API Service层（V1.1修复版）
│   │   ├── client.ts           # Axios配置（带/api/v1前缀）
│   │   ├── sop.ts              # SOP API
│   │   ├── task.ts             # Task API
│   │   ├── adapter.ts          # Adapter API
│   │   └── types.ts            # API类型定义
│   ├── /components
│   │   ├── /Layout
│   │   │   ├── AppLayout.tsx
│   │   │   └── Navbar.tsx
│   │   ├── /SOP
│   │   │   ├── SOPCard.tsx
│   │   │   ├── SOPList.tsx
│   │   │   └── SOPDeleteModal.tsx
│   │   ├── /Task
│   │   │   ├── StepCard.tsx
│   │   │   ├── StepProgress.tsx
│   │   │   └── TaskTimeline.tsx
│   │   ├── /Monitor
│   │   │   ├── JointStatusTable.tsx
│   │   │   ├── SensorDataCard.tsx
│   │   │   └── FaultList.tsx
│   │   ├── /Admin
│   │   │   └── SeedDataGuide.tsx   # ✅ P0-3修复：新增
│   │   └── /Viewer3D
│   │       ├── RobotModel.tsx
│   │       └── JointHighlight.tsx
│   ├── /hooks
│   │   ├── useWebSocket.ts          # V1.1修复版
│   │   ├── useTaskExecution.ts
│   │   └── useRobotState.ts
│   ├── /pages
│   │   ├── HomePage.tsx
│   │   ├── SOPListPage.tsx
│   │   ├── TaskExecutionPage.tsx
│   │   ├── MonitorPage.tsx
│   │   ├── ReportPage.tsx
│   │   └── /admin
│   │       ├── FaultManagePage.tsx
│   │       └── SeedDataPage.tsx     # ✅ P0-3修复：改为说明页
│   ├── /store
│   │   ├── taskStore.ts
│   │   ├── robotStore.ts
│   │   └── uiStore.ts
│   ├── /types
│   │   ├── sop.ts
│   │   ├── task.ts
│   │   └── robot.ts
│   ├── /utils
│   │   ├── format.ts
│   │   └── validation.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── vite-env.d.ts
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

***

## 3. API通信规范（V1.1修复版）

### 3.1 HTTP API路径规范（V1.1强制约束）

**文件：** `src/api/client.ts`

```
/**
 * Axios客户端配置（V1.1修复版）
 * 
 * ⚠️ 强制约束（遵循骨架文档§2.3和§4.6）：
 * - 所有HTTP API必须包含 /api/v1/ 前缀
 * - WebSocket连接必须使用 /ws/robot/status 路径
 */
import axios, { AxiosError, AxiosResponse } from 'axios';
import { message } from 'antd';

// API基础路径配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// 创建Axios实例（V1.1修正：添加/api/v1前缀）
export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,  // ✅ 强制约束：统一添加前缀
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可添加认证Token（MVP阶段暂不需要）
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器（V1.1修正：遵循骨架文档§4.7错误格式）
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response) {
      const errorData = error.response.data;
      
      // 统一错误提示
      const errorMessage = errorData?.message || '请求失败，请稍后重试';
      message.error(errorMessage);
      
      // 业务规则违反（409）特殊处理
      if (error.response.status === 409) {
        console.warn('Business rule violation:', errorData);
      }
    } else if (error.request) {
      message.error('网络连接失败，请检查网络');
    } else {
      message.error('请求配置错误');
    }
    
    return Promise.reject(error);
  }
);

// 错误响应类型（遵循骨架文档§4.7）
export interface ErrorResponse {
  status_code: number;
  error_type: string;
  message: string;
  details?: {
    code: string;
    message: string;
    field?: string;
    details?: Record<string, any>;
  };
  timestamp: string;
  request_id?: string;
}
```

***

### 3.2 WebSocket连接规范（V1.1修复版）

**文件：** `src/hooks/useWebSocket.ts`

```
/**
 * WebSocket连接Hook（V1.1修复版）
 * 
 * ⚠️ 强制约束（遵循骨架文档§2.3）：
 * - WebSocket路径必须为 /ws/robot/status
 * - 消息格式必须包含 type、timestamp、payload
 */
import { useEffect, useRef, useState } from 'react';
import { message } from 'antd';

// WebSocket配置
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
const WS_RECONNECT_INTERVAL = 5000; // 5秒重连
const WS_MAX_RETRIES = 3;

// 遥测消息类型（遵循骨架文档§4.4）
export interface TelemetryMessage {
  type: 'telemetry';
  timestamp: string;
  payload: {
    joints: JointState[];
    sensors: SensorData;
    active_faults: string[];
  };
}

export interface JointState {
  joint_id: string;
  position: number;
  velocity: number;
  torque?: number;
  current?: number;
  temperature?: number;
  error_code?: string;
}

export interface SensorData {
  imu?: {
    acceleration: { x: number; y: number; z: number };
    angular_velocity: { x: number; y: number; z: number };
    orientation?: { x: number; y: number; z: number; w: number };
  };
  battery?: number;
  temperature?: number;
  voltage?: Record<string, number>;
  pressure?: Record<string, number>;
}

export interface UseWebSocketResult {
  isConnected: boolean;
  telemetryData: TelemetryMessage['payload'] | null;
  error: string | null;
  reconnect: () => void;
}

export const useWebSocket = (): UseWebSocketResult => {
  const [isConnected, setIsConnected] = useState(false);
  const [telemetryData, setTelemetryData] = useState<TelemetryMessage['payload'] | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = () => {
    try {
      // ✅ V1.1修正：使用正确的WebSocket路径
      const wsUrl = `${WS_BASE_URL}/ws/robot/status`;
      console.log('Connecting to WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
        retryCountRef.current = 0;
        message.success('实时监控已连接');
      };

      ws.onmessage = (event) => {
        try {
          const data: TelemetryMessage = JSON.parse(event.data);
          
          // 验证消息格式（遵循骨架文档§4.4）
          if (data.type === 'telemetry' && data.payload) {
            setTelemetryData(data.payload);
          } else {
            console.warn('Unknown message format:', data);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket连接错误');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // 自动重连逻辑
        if (retryCountRef.current < WS_MAX_RETRIES) {
          retryCountRef.current += 1;
          console.log(`Reconnecting... (${retryCountRef.current}/${WS_MAX_RETRIES})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, WS_RECONNECT_INTERVAL);
        } else {
          setError('WebSocket连接失败，请刷新页面');
          message.error('实时监控连接失败');
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setError('WebSocket初始化失败');
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const reconnect = () => {
    disconnect();
    retryCountRef.current = 0;
    connect();
  };

  useEffect(() => {
    connect();
    return () => disconnect();
  }, []);

  return {
    isConnected,
    telemetryData,
    error,
    reconnect,
  };
};
```

***

## 4. 核心页面实现

### 4.1 SOP列表页

**文件：** `src/pages/SOPListPage.tsx`

```
/**
 * SOP列表页
 */
import React, { useEffect, useState } from 'react';
import { Button, Table, Tag, Space, message } from 'antd';
import { PlusOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { listSOPs } from '@/api/sop';
import { SOPListItem } from '@/types/sop';

const SOPListPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [sops, setSOPs] = useState<SOPListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const fetchSOPs = async () => {
    setLoading(true);
    try {
      const response = await listSOPs({
        skip: (page - 1) * pageSize,
        limit: pageSize,
      });
      setSOPs(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('加载SOP列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSOPs();
  }, [page, pageSize]);

  const handleCreateTask = (sop: SOPListItem) => {
    navigate('/task/create', { state: { sopId: sop.id, sopName: sop.name } });
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'SOP名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => <Tag>{category || '未分类'}</Tag>,
    },
    {
      title: '难度',
      dataIndex: 'difficulty_level',
      key: 'difficulty_level',
      render: (level: string) => {
        const colorMap = { low: 'green', medium: 'orange', high: 'red' };
        return <Tag color={colorMap[level]}>{level}</Tag>;
      },
    },
    {
      title: '步骤数',
      dataIndex: 'step_count',
      key: 'step_count',
    },
    {
      title: '预估时长',
      dataIndex: 'estimated_time',
      key: 'estimated_time',
      render: (seconds: number) => `${Math.round(seconds / 60)}分钟`,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: SOPListItem) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => handleCreateTask(record)}
          >
            开始训练
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>标准操作流程（SOP）</h2>
        <Button type="primary" icon={<PlusOutlined />}>
          创建SOP
        </Button>
      </div>
      
      <Table
        columns={columns}
        dataSource={sops}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          onChange: (page, pageSize) => {
            setPage(page);
            setPageSize(pageSize);
          },
        }}
      />
    </div>
  );
};

export default SOPListPage;
```

***

### 4.2 Task执行页

**文件：** `src/pages/TaskExecutionPage.tsx`

```
/**
 * Task执行页（V1.1修复版）
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Steps, Card, message, Modal } from 'antd';
import { PlayCircleOutlined, PauseOutlined } from '@ant-design/icons';
import { getTask, executeStep, pauseTask, resumeTask } from '@/api/task';
import { Task, StepExecutionResponse } from '@/types/task';
import { SOPStep } from '@/types/sop';

const TaskExecutionPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  
  const [task, setTask] = useState<Task | null>(null);
  const [steps, setSteps] = useState<SOPStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    if (taskId) {
      loadTask(parseInt(taskId));
    }
  }, [taskId]);

  const loadTask = async (id: number) => {
    setLoading(true);
    try {
      const taskData = await getTask(id);
      setTask(taskData);
      setSteps(taskData.sop.steps);
    } catch (error) {
      message.error('加载任务失败');
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

  if (loading || !task) {
    return <div>加载中...</div>;
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
```

***

## 5. 管理功能页面（V1.2修复版）

### 5.1 故障案例管理

**文件：** `src/pages/admin/FaultManagePage.tsx`

```
/**
 * 故障案例管理页面
 */
import React, { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { listFaultCases } from '@/api/fault';
import { FaultCase } from '@/types/fault';

const FaultManagePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [faults, setFaults] = useState<FaultCase[]>([]);

  const fetchFaults = async () => {
    setLoading(true);
    try {
      const data = await listFaultCases();
      setFaults(data);
    } catch (error) {
      message.error('加载故障案例失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFaults();
  }, []);

  const columns = [
    {
      title: '故障代码',
      dataIndex: 'fault_code',
      key: 'fault_code',
    },
    {
      title: '故障名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colorMap = { low: 'green', medium: 'orange', high: 'red' };
        return <Tag color={colorMap[severity]}>{severity}</Tag>;
      },
    },
    {
      title: '推荐SOP',
      dataIndex: 'recommended_sop_id',
      key: 'recommended_sop_id',
      render: (sopId: number) => sopId || '未关联',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: FaultCase) => (
        <Space>
          <Button icon={<EditOutlined />} size="small">
            编辑
          </Button>
          <Button icon={<DeleteOutlined />} size="small" danger>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>故障案例库管理</h2>
        <Button type="primary" icon={<PlusOutlined />}>
          添加故障案例
        </Button>
      </div>
      
      <Table
        columns={columns}
        dataSource={faults}
        rowKey="id"
        loading={loading}
      />
    </div>
  );
};

export default FaultManagePage;
```

***

### 5.2 种子数据管理（✅ P0-3修复）

**文件：** `src/pages/admin/SeedDataPage.tsx`

```
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
```

***

### 5.2.1 种子数据说明组件（可复用）

**文件：** `src/components/Admin/SeedDataGuide.tsx`

```
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
```

***

## 6. 关键组件实现

### 6.1 步骤执行组件

**文件：** `src/components/Task/StepCard.tsx`

```
/**
 * 步骤卡片组件（V1.1修复版）
 */
import React from 'react';
import { Card, Button, Tag, Space } from 'antd';
import { PlayCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { SOPStep } from '@/types/sop';

interface StepCardProps {
  step: SOPStep;
  currentStepIndex: number;
  onExecute: (stepIndex: number) => void;
  executing: boolean;
}

const StepCard: React.FC<StepCardProps> = ({ 
  step, 
  currentStepIndex, 
  onExecute,
  executing 
}) => {
  const isActive = step.step_index === currentStepIndex + 1;
  const isCompleted = step.step_index <= currentStepIndex;
  
  return (
    <Card
      style={{
        marginBottom: 16,
        borderColor: isActive ? '#1890ff' : undefined,
        background: isCompleted ? '#f6ffed' : undefined,
      }}
      extra={
        isCompleted ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            已完成
          </Tag>
        ) : isActive ? (
          <Tag color="processing">进行中</Tag>
        ) : (
          <Tag>待执行</Tag>
        )
      }
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <strong>步骤 {step.step_index}:</strong> {step.title}
        </div>
        <div>{step.description}</div>
        
        {step.is_critical && (
          <Tag color="red">关键步骤</Tag>
        )}
        
        {isActive && (
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => onExecute(step.step_index)}
            loading={executing}
          >
            执行此步骤
          </Button>
        )}
      </Space>
    </Card>
  );
};

export default StepCard;
```

***

## 7. 3D可视化实现

**文件：** `src/components/Viewer3D/RobotModel.tsx`

```
/**
 * 3D机器人模型组件
 */
import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { JointState } from '@/types/robot';

interface RobotModelProps {
  joints: JointState[];
}

const Robot: React.FC<{ joints: JointState[] }> = ({ joints }) => {
  const groupRef = useRef<THREE.Group>(null);
  
  // 简化的机器人渲染（使用球体和圆柱体表示关节）
  return (
    <group ref={groupRef}>
      {joints.map((joint, index) => (
        <mesh key={joint.joint_id} position={[index * 2, 0, 0]}>
          <sphereGeometry args={[0.5, 32, 32]} />
          <meshStandardMaterial 
            color={joint.error_code ? '#ff4d4f' : '#52c41a'} 
          />
        </mesh>
      ))}
    </group>
  );
};

const RobotModel: React.FC<RobotModelProps> = ({ joints }) => {
  return (
    <Canvas camera={{ position:, fov: 50 }}>[1]
      <ambientLight intensity={0.5} />
      <pointLight position={} />
      <Robot joints={joints} />
      <OrbitControls />
    </Canvas>
  );
};

export default RobotModel;
```

***

## 8. 状态管理

**文件：** `src/store/taskStore.ts`

```
/**
 * Task状态管理（使用Zustand）
 */
import { create } from 'zustand';
import { Task } from '@/types/task';

interface TaskStore {
  currentTask: Task | null;
  setCurrentTask: (task: Task | null) => void;
  executing: boolean;
  setExecuting: (executing: boolean) => void;
}

export const useTaskStore = create<TaskStore>((set) => ({
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),
  executing: false,
  setExecuting: (executing) => set({ executing }),
}));
```

***

## 9. 验收标准

### 9.1 功能验收

| 验收项 | 验收标准 | 验收方法 |
|-------|---------|---------|
| SOP列表加载 | 成功显示所有SOP | 手动测试 |
| Task创建 | 可从SOP创建Task | 手动测试 |
| 步骤执行 | 可顺序执行步骤 | 手动测试 |
| WebSocket连接 | 实时监控数据更新 | 手动测试 |
| 3D可视化 | 机器人模型正常显示 | 手动测试 |
| ✅ P0-3验收 | 种子数据页面显示SSH说明 | 手动测试 |

### 9.2 API集成验收

| 验收项 | 验收标准 | 验证方法 |
|-------|---------|---------|
| API路径 | 所有请求包含/api/v1前缀 | 浏览器Network检查 |
| WebSocket路径 | 连接/ws/robot/status | 浏览器Network检查 |
| 错误处理 | 显示后端错误消息 | 手动触发错误 |
| 响应字段 | 正确解析所有字段 | 代码审查 |

***

## 10. 交付清单

- [x] `src/api/client.ts` - Axios配置（V1.1修复版）
- [x] `src/api/sop.ts` - SOP API
- [x] `src/api/task.ts` - Task API（V1.1修复版）
- [x] `src/hooks/useWebSocket.ts` - WebSocket Hook（V1.1修复版）
- [x] `src/pages/SOPListPage.tsx` - SOP列表页
- [x] `src/pages/TaskExecutionPage.tsx` - Task执行页（V1.1修复版）
- [x] `src/pages/admin/SeedDataPage.tsx` - 种子数据说明页（✅ P0-3修复）
- [x] `src/components/Admin/SeedDataGuide.tsx` - 种子数据说明组件（✅ P0-3新增）
- [x] `src/components/Task/StepCard.tsx` - 步骤卡片组件
- [x] `src/components/Viewer3D/RobotModel.tsx` - 3D模型组件
- [x] `src/store/taskStore.ts` - 状态管理
- [x] `package.json` - 依赖配置
- [x] `tsconfig.json` - TypeScript配置
- [x] `vite.config.ts` - Vite配置
- [x] `README.md` - 项目说明

***

**文档状态**: ✅ V1.2 P0修复完成  
**最后更新**: 2025-12-30  
**修复状态**: ✅ P0-3（种子数据API）已修复为SSH说明
```

***

