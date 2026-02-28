// Diagnosis Report Page
// P1: Diagnosis and Root Cause Analysis

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Tag, Progress, List, Button, Spin, Result, Badge } from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  QuestionCircleOutlined,
  ArrowLeftOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { diagnoseError } from '@/api/agent';

interface Finding {
  code: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
}

interface Recommendation {
  code: string;
  message: string;
  priority: 'high' | 'medium' | 'low';
}

const severityColors: Record<string, string> = {
  info: 'blue',
  warning: 'orange',
  error: 'red',
  critical: 'magenta',
};

const priorityColors: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
};

const DiagnosisPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [diagnosis, setDiagnosis] = useState<{
    root_cause?: string;
    root_cause_confidence: number;
    findings: Finding[];
    recommendations: Recommendation[];
    evidence_refs: string[];
    baseline_comparison?: {
      baseline_value: number;
      actual_value: number;
      deviation_percent: number;
    };
  } | null>(null);

  useEffect(() => {
    if (taskId) {
      loadDiagnosis(parseInt(taskId));
    }
  }, [taskId]);

  const loadDiagnosis = async (id: number) => {
    setLoading(true);
    try {
      // Mock data - in production, call diagnoseError API
      // const result = await diagnoseError(...);

      // Mock response
      setDiagnosis({
        root_cause: 'habit_issue',
        root_cause_confidence: 0.75,
        findings: [
          { code: 'TOO_FAST', message: '操作速度过快，平均耗时 < 5秒', severity: 'warning' },
          { code: 'SKIP_CHECK', message: '检测步骤被跳过', severity: 'error' },
        ],
        recommendations: [
          { code: 'FORCE_PAUSE', message: '强制停顿确认', priority: 'high' },
          { code: 'ADD_CHECKPOINT', message: '添加检查点', priority: 'medium' },
        ],
        evidence_refs: ['ev-001', 'ev-002', 'ev-003'],
        baseline_comparison: {
          baseline_value: 60000,
          actual_value: 45000,
          deviation_percent: -25,
        },
      });
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const rootCauseLabels: Record<string, string> = {
    concept_misunderstanding: '概念理解偏差',
    habit_issue: '操作习惯问题',
    attention_issue: '注意力分散',
    tool_selection_error: '工具选择错误',
    sequence_error: '操作顺序错误',
    unknown: '未知',
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>分析诊断中...</p>
      </div>
    );
  }

  if (!diagnosis) {
    return (
      <Result
        status="error"
        title="无法加载诊断报告"
        extra={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
            返回任务列表
          </Button>
        }
      />
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <h2 style={{ margin: 0 }}>
              <ExperimentOutlined style={{ marginRight: 8 }} />
              诊断报告
            </h2>
          </Col>
          <Col>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/reports/${taskId}`)}>
              返回报告
            </Button>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        {/* Left Column - Root Cause */}
        <Col xs={24} lg={12}>
          <Card title="根因分析" style={{ marginBottom: 16 }}>
            {diagnosis.root_cause ? (
              <>
                <div style={{ textAlign: 'center', marginBottom: 24 }}>
                  <Tag color="red" style={{ fontSize: 16, padding: '8px 16px' }}>
                    {rootCauseLabels[diagnosis.root_cause] || diagnosis.root_cause}
                  </Tag>
                </div>
                <Progress
                  type="circle"
                  percent={Math.round(diagnosis.root_cause_confidence * 100)}
                  format={(percent) => `${percent}% 置信度`}
                  status={diagnosis.root_cause_confidence > 0.7 ? 'success' : 'normal'}
                />
              </>
            ) : (
              <Result
                status="success"
                title="未发现问题"
                subTitle="您的操作符合标准"
              />
            )}
          </Card>

          {/* Baseline Comparison */}
          {diagnosis.baseline_comparison && (
            <Card title="基线对照" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: '#666' }}>标准时长</div>
                    <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                      {diagnosis.baseline_comparison.baseline_value / 1000}秒
                    </div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: '#666' }}>实际时长</div>
                    <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                      {diagnosis.baseline_comparison.actual_value / 1000}秒
                    </div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: '#666' }}>偏差</div>
                    <div
                      style={{
                        fontSize: 24,
                        fontWeight: 'bold',
                        color:
                          Math.abs(diagnosis.baseline_comparison.deviation_percent) > 20
                            ? '#ff4d4f'
                            : '#52c41a',
                      }}
                    >
                      {diagnosis.baseline_comparison.deviation_percent > 0 ? '+' : ''}
                      {diagnosis.baseline_comparison.deviation_percent.toFixed(0)}%
                    </div>
                  </div>
                </Col>
              </Row>
            </Card>
          )}

          {/* Evidence References */}
          <Card title="证据引用">
            <div>
              {diagnosis.evidence_refs.map((ref) => (
                <Tag key={ref} color="blue" style={{ marginBottom: 8 }}>
                  {ref}
                </Tag>
              ))}
            </div>
          </Card>
        </Col>

        {/* Right Column - Findings & Recommendations */}
        <Col xs={24} lg={12}>
          {/* Findings */}
          <Card title="发现项" style={{ marginBottom: 16 }}>
            <List
              dataSource={diagnosis.findings}
              renderItem={(item) => (
                <List.Item>
                  <Badge
                    status={
                      item.severity === 'error'
                        ? 'error'
                        : item.severity === 'warning'
                        ? 'warning'
                        : 'processing'
                    }
                  />
                  <Tag color={severityColors[item.severity]}>{item.severity}</Tag>
                  <span>{item.message}</span>
                </List.Item>
              )}
            />
          </Card>

          {/* Recommendations */}
          <Card title="改进建议">
            <List
              dataSource={diagnosis.recommendations}
              renderItem={(item, index) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <Badge
                        count={index + 1}
                        style={{ backgroundColor: priorityColors[item.priority] }}
                      />
                    }
                    title={<Tag color={priorityColors[item.priority]}>{item.priority}</Tag>}
                    description={item.message}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default DiagnosisPage;
