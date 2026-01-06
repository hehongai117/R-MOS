/**
 * 错误边界组件
 * 捕获子组件的 JavaScript 错误，防止整个应用崩溃
 */
import { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button, Typography, Space } from 'antd';
import { ReloadOutlined, HomeOutlined, BugOutlined } from '@ant-design/icons';

const { Paragraph, Text } = Typography;

interface Props {
    children: ReactNode;
    /** 自定义错误回退 UI */
    fallback?: ReactNode;
    /** 错误发生时的回调 */
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
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

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        this.setState({ errorInfo });

        // 调用错误回调
        if (this.props.onError) {
            this.props.onError(error, errorInfo);
        }

        // 在开发环境中打印错误
        if (process.env.NODE_ENV === 'development') {
            console.error('ErrorBoundary caught an error:', error);
            console.error('Component stack:', errorInfo.componentStack);
        }

        // TODO: 可以在这里发送错误报告到服务端
    }

    handleReload = (): void => {
        window.location.reload();
    };

    handleGoHome = (): void => {
        window.location.href = '/';
    };

    handleReset = (): void => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
        });
    };

    render(): ReactNode {
        const { hasError, error, errorInfo } = this.state;
        const { children, fallback } = this.props;

        if (hasError) {
            // 如果提供了自定义回退 UI，使用它
            if (fallback) {
                return fallback;
            }

            // 默认错误 UI
            return (
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minHeight: '100vh',
                        background: '#f5f5f5',
                        padding: 24,
                    }}
                >
                    <Result
                        status="error"
                        title="页面出错了"
                        subTitle="抱歉，页面遇到了一些问题。请尝试刷新页面或返回首页。"
                        extra={
                            <Space>
                                <Button
                                    type="primary"
                                    icon={<ReloadOutlined />}
                                    onClick={this.handleReload}
                                >
                                    刷新页面
                                </Button>
                                <Button
                                    icon={<HomeOutlined />}
                                    onClick={this.handleGoHome}
                                >
                                    返回首页
                                </Button>
                            </Space>
                        }
                    >
                        {/* 开发模式下显示错误详情 */}
                        {process.env.NODE_ENV === 'development' && error && (
                            <div
                                style={{
                                    textAlign: 'left',
                                    marginTop: 24,
                                    padding: 16,
                                    background: '#fff1f0',
                                    borderRadius: 8,
                                    border: '1px solid #ffccc7',
                                }}
                            >
                                <Paragraph>
                                    <BugOutlined style={{ marginRight: 8, color: '#ff4d4f' }} />
                                    <Text strong style={{ color: '#ff4d4f' }}>
                                        开发模式错误详情
                                    </Text>
                                </Paragraph>
                                <Paragraph>
                                    <Text code>{error.name}: {error.message}</Text>
                                </Paragraph>
                                {errorInfo && (
                                    <Paragraph>
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            <pre style={{
                                                maxHeight: 200,
                                                overflow: 'auto',
                                                margin: 0,
                                                whiteSpace: 'pre-wrap',
                                            }}>
                                                {errorInfo.componentStack}
                                            </pre>
                                        </Text>
                                    </Paragraph>
                                )}
                            </div>
                        )}
                    </Result>
                </div>
            );
        }

        return children;
    }
}

export default ErrorBoundary;
