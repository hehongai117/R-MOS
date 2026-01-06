/**
 * 全局加载状态组件
 * 提供多种加载样式：全屏、内联、骨架屏
 */
import React from 'react';
import { Spin, Skeleton } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface LoadingProps {
    /** 加载提示文字 */
    tip?: string;
    /** 加载类型：全屏覆盖 | 内联 | 骨架屏 */
    type?: 'fullscreen' | 'inline' | 'skeleton';
    /** 骨架屏行数 */
    rows?: number;
    /** 自定义样式 */
    style?: React.CSSProperties;
}

// 自定义加载图标
const loadingIcon = <LoadingOutlined style={{ fontSize: 32 }} spin />;

/**
 * 全屏加载覆盖层
 */
const FullscreenLoading: React.FC<{ tip?: string }> = ({ tip }) => (
    <div
        style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(255, 255, 255, 0.9)',
            zIndex: 9999,
        }}
    >
        <Spin indicator={loadingIcon} />
        {tip && (
            <div style={{ marginTop: 16, color: '#666', fontSize: 14 }}>
                {tip}
            </div>
        )}
    </div>
);

/**
 * 内联加载组件
 */
const InlineLoading: React.FC<{ tip?: string; style?: React.CSSProperties }> = ({
    tip,
    style
}) => (
    <div
        style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 40,
            ...style,
        }}
    >
        <Spin indicator={loadingIcon} />
        {tip && (
            <div style={{ marginTop: 12, color: '#666', fontSize: 14 }}>
                {tip}
            </div>
        )}
    </div>
);

/**
 * 骨架屏加载
 */
const SkeletonLoading: React.FC<{ rows?: number; style?: React.CSSProperties }> = ({
    rows = 4,
    style
}) => (
    <div style={{ padding: 24, ...style }}>
        <Skeleton active paragraph={{ rows }} />
    </div>
);

/**
 * Loading 组件
 */
const Loading: React.FC<LoadingProps> = ({
    tip = '加载中...',
    type = 'inline',
    rows = 4,
    style,
}) => {
    switch (type) {
        case 'fullscreen':
            return <FullscreenLoading tip={tip} />;
        case 'skeleton':
            return <SkeletonLoading rows={rows} style={style} />;
        case 'inline':
        default:
            return <InlineLoading tip={tip} style={style} />;
    }
};

// 导出子组件供单独使用
export { FullscreenLoading, InlineLoading, SkeletonLoading };
export default Loading;
