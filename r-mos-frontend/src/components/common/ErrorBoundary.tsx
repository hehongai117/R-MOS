/**
 * Error Boundary 组件（V2.3 新增）
 * 
 * 用于捕获 React 组件树中的 JavaScript 错误，
 * 提供降级 UI 而非整个页面崩溃。
 * 
 * 特别用于：
 * - 3D 视图加载失败
 * - WebGL 不支持
 * - 模型文件损坏
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button, Typography } from 'antd';
import { WarningOutlined, ReloadOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

interface Props {
    children: ReactNode;
    fallbackTitle?: string;
    fallbackMessage?: string;
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('[ErrorBoundary] 捕获到错误:', error);
        console.error('[ErrorBoundary] 组件堆栈:', errorInfo.componentStack);

        this.setState({ errorInfo });

        // 调用外部错误处理回调
        if (this.props.onError) {
            this.props.onError(error, errorInfo);
        }
    }

    handleRetry = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
        });
    };

    render() {
        const { hasError, error } = this.state;
        const { children, fallbackTitle, fallbackMessage } = this.props;

        if (hasError) {
            return (
                <Result
                    status="warning"
                    icon={<WarningOutlined />}
                    title={fallbackTitle || '组件加载失败'}
                    subTitle={fallbackMessage || '该区域暂时无法显示，请稍后重试'}
                    extra={[
                        <Button
                            key="retry"
                            type="primary"
                            icon={<ReloadOutlined />}
                            onClick={this.handleRetry}
                        >
                            重试
                        </Button>,
                    ]}
                >
                    {error && (
                        <Paragraph>
                            <Text type="secondary" code style={{ fontSize: 12 }}>
                                错误信息: {error.message}
                            </Text>
                        </Paragraph>
                    )}
                </Result>
            );
        }

        return children;
    }
}

/**
 * 3D 视图专用 Error Boundary
 * 
 * 预置了针对 3D/WebGL 的错误提示信息
 */
interface Viewer3DErrorBoundaryProps {
    children: ReactNode;
}

export const Viewer3DErrorBoundary: React.FC<Viewer3DErrorBoundaryProps> = ({ children }) => {
    return (
        <ErrorBoundary
            fallbackTitle="3D 视图不可用"
            fallbackMessage="3D 模型加载失败或您的浏览器不支持 WebGL。请尝试刷新页面或使用其他浏览器。"
            onError={(error) => {
                // 可以在这里上报错误到监控系统
                console.error('[Viewer3D] 3D 视图错误:', error);
            }}
        >
            {children}
        </ErrorBoundary>
    );
};

export default ErrorBoundary;
