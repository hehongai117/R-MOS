/**
 * WebSocket连接Hook（V2.3 增强版 - 鲁棒性提升）
 * 
 * 新增功能：
 * - 指数退避重连 (Exponential Backoff)
 * - Ping/Pong 心跳响应
 * - 连接状态详细追踪
 * - 数据过期检测
 * 
 * ⚠️ 强制约束（遵循骨架文档§2.3）：
 * - WebSocket路径必须为 /ws/robot/status
 * - 消息格式必须包含 type、timestamp、payload
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { message } from 'antd';

// WebSocket配置
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
const WS_MAX_RETRIES = 10;
const WS_BASE_DELAY = 1000; // 初始重连延迟 1秒
const WS_MAX_DELAY = 30000; // 最大重连延迟 30秒
const DATA_STALE_THRESHOLD = 5000; // 数据过期阈值 5秒

// 遥测消息类型（遵循骨架文档§4.4）
export interface TelemetryMessage {
  type: 'telemetry' | 'ping' | 'pong';
  timestamp: string;
  payload?: {
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

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'failed';

export interface UseWebSocketResult {
  status: ConnectionStatus;
  isConnected: boolean;
  isDataStale: boolean;
  telemetryData: TelemetryMessage['payload'] | null;
  lastUpdateTime: Date | null;
  error: string | null;
  retryCount: number;
  reconnect: () => void;
}

/**
 * 计算指数退避延迟
 */
const calculateBackoff = (retryCount: number): number => {
  const delay = Math.min(WS_BASE_DELAY * Math.pow(2, retryCount), WS_MAX_DELAY);
  // 添加 10% 抖动避免雷群效应
  const jitter = delay * 0.1 * Math.random();
  return delay + jitter;
};

export const useWebSocket = (): UseWebSocketResult => {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [telemetryData, setTelemetryData] = useState<TelemetryMessage['payload'] | null>(null);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [isDataStale, setIsDataStale] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const staleCheckIntervalRef = useRef<NodeJS.Timeout>();

  // 检测数据是否过期
  useEffect(() => {
    staleCheckIntervalRef.current = setInterval(() => {
      if (lastUpdateTime) {
        const stale = Date.now() - lastUpdateTime.getTime() > DATA_STALE_THRESHOLD;
        setIsDataStale(stale);
      }
    }, 1000);

    return () => {
      if (staleCheckIntervalRef.current) {
        clearInterval(staleCheckIntervalRef.current);
      }
    };
  }, [lastUpdateTime]);

  const connect = useCallback(() => {
    try {
      setStatus('connecting');
      const wsUrl = `${WS_BASE_URL}/ws/robot/status`;
      console.log('[WS] 正在连接:', wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] 连接成功');
        setStatus('connected');
        setError(null);
        setRetryCount(0);
        setIsDataStale(false);
        message.success('实时监控已连接');
      };

      ws.onmessage = (event) => {
        try {
          const data: TelemetryMessage = JSON.parse(event.data);

          // 处理心跳 Ping
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            console.log('[WS] 心跳响应已发送');
            return;
          }

          // 处理遥测数据
          if (data.type === 'telemetry' && data.payload) {
            setTelemetryData(data.payload);
            setLastUpdateTime(new Date());
            setIsDataStale(false);
          }
        } catch (err) {
          console.error('[WS] 消息解析失败:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[WS] 连接错误:', event);
        setError('WebSocket连接错误');
      };

      ws.onclose = (event) => {
        console.log('[WS] 连接断开, code:', event.code, 'reason:', event.reason);
        setStatus('disconnected');
        setIsDataStale(true);

        // 指数退避重连
        if (retryCount < WS_MAX_RETRIES) {
          const delay = calculateBackoff(retryCount);
          console.log(`[WS] 将在 ${Math.round(delay / 1000)}s 后重连 (${retryCount + 1}/${WS_MAX_RETRIES})`);
          setStatus('reconnecting');
          setRetryCount(prev => prev + 1);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setStatus('failed');
          setError('WebSocket连接失败，已达最大重试次数');
          message.error('实时监控连接失败，请手动刷新');
        }
      };
    } catch (err) {
      console.error('[WS] 初始化失败:', err);
      setError('WebSocket初始化失败');
      setStatus('failed');
    }
  }, [retryCount]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'User requested disconnect');
      wsRef.current = null;
    }
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    setRetryCount(0);
    setError(null);
    connect();
  }, [disconnect, connect]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, []);

  return {
    status,
    isConnected: status === 'connected',
    isDataStale,
    telemetryData,
    lastUpdateTime,
    error,
    retryCount,
    reconnect,
  };
};

