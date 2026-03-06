// AI Chat Page
// P1: AI Conversation Interface

import React, { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, List, Avatar, Spin, message } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { sendAgentRequest } from '@/api/agent';
import { useAuthStore } from '@/store/authStore'

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  action?: {
    type: string;
    target?: string;
    explanation?: string;
  };
}

const normalizeSuggestedAction = (
  action: Record<string, unknown> | undefined
): ChatMessage['action'] | undefined => {
  if (!action) return undefined;
  const type = typeof action.type === 'string' ? action.type : '';
  if (!type) return undefined;
  return {
    type,
    target: typeof action.target === 'string' ? action.target : undefined,
    explanation: typeof action.explanation === 'string' ? action.explanation : undefined,
  };
};

const AIChatPage: React.FC = () => {
  const user = useAuthStore((state) => state.user)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '您好！我是您的维保培训智能助手。您可以告诉我：\n• "今天想练习减速器维修"\n• "下一步该做什么"\n• "我遇到问题了"\n\n我会根据您的需求提供个性化的指导和建议。',
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendAgentRequest({
        user_id: user?.user_id ? String(user.user_id) : 'anonymous',
        message: userMessage.content,
        context: {},
      });

      const assistantMessage: ChatMessage = {
        id: response.response_id,
        role: 'assistant',
        content: response.message,
        timestamp: Date.now(),
        action: normalizeSuggestedAction(response.action_suggested),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: unknown) {
      message.error('智能助手暂时无法响应，请稍后再试');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Quick action buttons
  const quickActions = [
    { label: '开始练习', prompt: '我想开始练习维保操作' },
    { label: '查看任务', prompt: '查看我的当前任务' },
    { label: '请求帮助', prompt: '我需要帮助' },
    { label: '诊断问题', prompt: '我遇到了问题，请帮我诊断' },
  ];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '24px', height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <Card
        title={
          <span>
            <RobotOutlined style={{ marginRight: 8 }} />
            智能助手
          </span>
        }
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' } }}
      >
        {/* Quick Actions */}
        <div style={{ marginBottom: 16 }}>
          <span style={{ color: '#666', marginRight: 8 }}>快速操作:</span>
          {quickActions.map((action) => (
            <Button
              key={action.label}
              size="small"
              style={{ marginRight: 8, marginBottom: 8 }}
              onClick={() => {
                setInput(action.prompt);
                handleSend();
              }}
            >
              {action.label}
            </Button>
          ))}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px 0' }}>
          <List
            dataSource={messages}
            renderItem={(item) => (
              <List.Item
                style={{
                  justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
                  border: 'none',
                  padding: '8px 0',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    flexDirection: item.role === 'user' ? 'row-reverse' : 'row',
                    alignItems: 'flex-start',
                    maxWidth: '80%',
                  }}
                >
                  <Avatar
                    icon={item.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                      backgroundColor: item.role === 'user' ? '#1890ff' : '#52c41a',
                      marginLeft: item.role === 'user' ? 8 : 0,
                      marginRight: item.role === 'user' ? 0 : 8,
                    }}
                  />
                  <div
                    style={{
                      background: item.role === 'user' ? '#e6f7ff' : '#f6ffed',
                      padding: '12px 16px',
                      borderRadius: 8,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {item.content}
                    {item.action && (
                      <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #d9d9d9' }}>
                        <QuestionCircleOutlined /> 建议操作: {item.action.type}
                        {item.action.target && ` - ${item.action.target}`}
                      </div>
                    )}
                  </div>
                </div>
              </List.Item>
            )}
          />
          {loading && (
            <div style={{ textAlign: 'center', padding: '16px' }}>
              <Spin tip="智能助手思考中..." />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16, display: 'flex' }}>
          <Input.TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题或需求..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1, marginRight: 8 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={!input.trim()}
          >
            发送
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default AIChatPage;
