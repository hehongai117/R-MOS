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
