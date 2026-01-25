/**
 * 机器人实时数据 Hook
 * 
 * 连接 WebSocket 获取机器人关节状态、传感器数据和故障信息
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { JointState } from '@/types/robot';
import { WS_CONFIG } from '../constants';

interface SensorData {
    sensor_id: string;
    value: number;
    unit: string;
    timestamp: string;
}

interface FaultInfo {
    fault_code: string;
    fault_type: string;
    severity: string;
    target_part: string;
    description: string;
    injected_at: string;
}

interface RobotStatusMessage {
    type: 'robot_status';
    data: {
        joints: JointState[];
        sensors: SensorData[];
        faults: FaultInfo[];
        timestamp: string;
    };
}

interface UseRobotDataReturn {
    /** 关节状态列表 */
    joints: JointState[];
    /** 传感器数据列表 */
    sensors: SensorData[];
    /** 故障信息列表 */
    faults: FaultInfo[];
    /** WebSocket 连接状态 */
    connected: boolean;
    /** 连接错误 */
    error: Error | null;
    /** 手动重连 */
    reconnect: () => void;
    /** 最后更新时间 */
    lastUpdate: Date | null;
}

/**
 * 机器人实时数据 Hook
 */
export function useRobotData(wsUrl?: string): UseRobotDataReturn {
    const url = wsUrl || WS_CONFIG.url;

    const [joints, setJoints] = useState<JointState[]>([]);
    const [sensors, setSensors] = useState<SensorData[]>([]);
    const [faults, setFaults] = useState<FaultInfo[]>([]);
    const [connected, setConnected] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const throttleRef = useRef<NodeJS.Timeout | null>(null);
    const pendingDataRef = useRef<RobotStatusMessage['data'] | null>(null);

    /**
     * 处理消息（带节流）
     */
    const processData = useCallback((data: RobotStatusMessage['data']) => {
        setJoints(data.joints || []);
        setSensors(data.sensors || []);
        setFaults(data.faults || []);
        setLastUpdate(new Date());
    }, []);

    /**
     * 消息处理
     */
    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message: RobotStatusMessage = JSON.parse(event.data);

            if (message.type === 'robot_status') {
                // 节流处理
                if (throttleRef.current) {
                    pendingDataRef.current = message.data;
                    return;
                }

                processData(message.data);

                throttleRef.current = setTimeout(() => {
                    throttleRef.current = null;
                    if (pendingDataRef.current) {
                        processData(pendingDataRef.current);
                        pendingDataRef.current = null;
                    }
                }, WS_CONFIG.throttleMs);
            }
        } catch (err) {
            console.error('WebSocket 消息解析失败:', err);
        }
    }, [processData]);

    /**
     * 连接 WebSocket
     */
    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            const token = localStorage.getItem('access_token');
            const wsUrlWithAuth = token ? `${url}?token=${token}` : url;

            const ws = new WebSocket(wsUrlWithAuth);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('WebSocket 已连接');
                setConnected(true);
                setError(null);
                reconnectAttemptsRef.current = 0;
            };

            ws.onmessage = handleMessage;

            ws.onerror = (event) => {
                console.error('WebSocket 错误:', event);
                setError(new Error('WebSocket 连接错误'));
            };

            ws.onclose = (event) => {
                console.log('WebSocket 已关闭:', event.code, event.reason);
                setConnected(false);
                wsRef.current = null;

                // 自动重连
                if (reconnectAttemptsRef.current < WS_CONFIG.maxReconnectAttempts) {
                    reconnectAttemptsRef.current++;
                    console.log(`将在 ${WS_CONFIG.reconnectInterval}ms 后重连 (${reconnectAttemptsRef.current}/${WS_CONFIG.maxReconnectAttempts})`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, WS_CONFIG.reconnectInterval);
                } else {
                    setError(new Error('WebSocket 重连失败，已达最大重试次数'));
                }
            };
        } catch (err) {
            console.error('WebSocket 连接失败:', err);
            setError(err instanceof Error ? err : new Error('连接失败'));
        }
    }, [url, handleMessage]);

    /**
     * 手动重连
     */
    const reconnect = useCallback(() => {
        reconnectAttemptsRef.current = 0;
        if (wsRef.current) {
            wsRef.current.close();
        }
        connect();
    }, [connect]);

    /**
     * 初始化和清理
     */
    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (throttleRef.current) {
                clearTimeout(throttleRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connect]);

    return {
        joints,
        sensors,
        faults,
        connected,
        error,
        reconnect,
        lastUpdate,
    };
}

export default useRobotData;
