/**
 * DynamicModelLoader.tsx - 动态模型加载状态与错误处理 UI 组件
 *
 * 提供三个可复用组件：
 * - ModelLoadingFallback: 带进度条的加载指示器
 * - ModelErrorFallback: 错误降级提示
 * - ModelEmptyFallback: 无模型占位
 */

import React from 'react';
import { Html, useProgress } from '@react-three/drei';

/**
 * ModelLoadingFallback - 3D Canvas 内的加载进度条
 * 使用 useProgress 获取真实加载百分比，通过 Html 渲染到 DOM 层
 */
export const ModelLoadingFallback: React.FC = () => {
    const { progress } = useProgress();
    const pct = Math.round(progress);

    return (
        <Html center>
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                fontFamily: 'monospace',
                color: '#4fc3f7',
                userSelect: 'none',
            }}>
                <div style={{ fontSize: '12px', letterSpacing: '0.05em' }}>加载中...</div>
                <div style={{
                    width: '120px',
                    height: '6px',
                    background: '#0d2137',
                    borderRadius: '3px',
                    overflow: 'hidden',
                }}>
                    <div style={{
                        width: `${pct}%`,
                        height: '100%',
                        background: '#4fc3f7',
                        borderRadius: '3px',
                        transition: 'width 0.2s ease',
                    }} />
                </div>
                <div style={{ fontSize: '11px' }}>{pct}%</div>
            </div>
        </Html>
    );
};

export interface ModelErrorFallbackProps {
    message?: string;
}

/**
 * ModelErrorFallback - 模型加载失败时的错误提示
 */
export const ModelErrorFallback: React.FC<ModelErrorFallbackProps> = ({
    message = '模型加载失败',
}) => {
    return (
        <Html center>
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                padding: '16px 20px',
                background: 'rgba(255, 107, 107, 0.15)',
                border: '1px solid rgba(255, 107, 107, 0.4)',
                borderRadius: '8px',
                maxWidth: '220px',
                textAlign: 'center',
            }}>
                <div style={{
                    color: '#ff6b6b',
                    fontSize: '14px',
                    fontWeight: 'bold',
                }}>
                    {message}
                </div>
                <div style={{
                    color: '#ff6b6b',
                    fontSize: '11px',
                    opacity: 0.8,
                }}>
                    请检查机器人是否已上传 3D 模型文件
                </div>
            </div>
        </Html>
    );
};

/**
 * ModelEmptyFallback - 无模型数据时的占位线框盒
 */
export const ModelEmptyFallback: React.FC = () => {
    return (
        <mesh>
            <boxGeometry args={[0.5, 0.5, 0.5]} />
            <meshStandardMaterial color="#4fc3f7" wireframe transparent opacity={0.3} />
        </mesh>
    );
};
