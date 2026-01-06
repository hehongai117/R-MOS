/**
 * 顶部导航栏组件
 * 包含系统标题、用户信息和全局操作
 */
import React from 'react';
import { Layout, Space, Button, Dropdown, Badge, Avatar, theme } from 'antd';
import {
    DashboardOutlined,
    BellOutlined,
    SettingOutlined,
    UserOutlined,
    LogoutOutlined,
    QuestionCircleOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header } = Layout;

interface NavbarProps {
    collapsed?: boolean;
    onToggleCollapse?: () => void;
}

const Navbar: React.FC<NavbarProps> = () => {
    const { token } = theme.useToken();

    // 用户下拉菜单
    const userMenuItems: MenuProps['items'] = [
        {
            key: 'profile',
            icon: <UserOutlined />,
            label: '个人信息',
        },
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: '系统设置',
        },
        {
            type: 'divider',
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '退出登录',
            danger: true,
        },
    ];

    // 通知下拉菜单
    const notificationItems: MenuProps['items'] = [
        {
            key: '1',
            label: '暂无新通知',
            disabled: true,
        },
    ];

    return (
        <Header
            style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 24px',
                background: token.colorBgContainer,
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
                height: 64,
                position: 'sticky',
                top: 0,
                zIndex: 100,
            }}
        >
            {/* 左侧 - 系统标题 */}
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                }}
            >
                <DashboardOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
                <span
                    style={{
                        fontSize: 18,
                        fontWeight: 600,
                        color: token.colorText,
                    }}
                >
                    R-MOS 机器人维护操作系统
                </span>
                <span
                    style={{
                        fontSize: 12,
                        color: token.colorTextSecondary,
                        background: token.colorFillSecondary,
                        padding: '2px 8px',
                        borderRadius: 4,
                    }}
                >
                    v2.3
                </span>
            </div>

            {/* 右侧 - 用户操作 */}
            <Space size="middle">
                {/* 帮助按钮 */}
                <Button
                    type="text"
                    icon={<QuestionCircleOutlined />}
                    title="帮助文档"
                />

                {/* 通知 */}
                <Dropdown menu={{ items: notificationItems }} trigger={['click']}>
                    <Badge count={0} size="small">
                        <Button type="text" icon={<BellOutlined />} />
                    </Badge>
                </Dropdown>

                {/* 用户信息 */}
                <Dropdown menu={{ items: userMenuItems }} trigger={['click']}>
                    <Space style={{ cursor: 'pointer' }}>
                        <Avatar size="small" icon={<UserOutlined />} />
                        <span style={{ color: token.colorText }}>管理员</span>
                    </Space>
                </Dropdown>
            </Space>
        </Header>
    );
};

export default Navbar;
