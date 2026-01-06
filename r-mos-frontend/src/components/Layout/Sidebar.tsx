/**
 * 侧边栏导航组件
 * 包含主导航菜单和折叠功能
 */
import React, { useState } from 'react';
import { Layout, Menu, theme } from 'antd';
import {
    FileTextOutlined,
    MonitorOutlined,
    WarningOutlined,
    DatabaseOutlined,
    BarChartOutlined,
    SettingOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import type { MenuProps } from 'antd';

const { Sider } = Layout;

type MenuItem = Required<MenuProps>['items'][number];

// 菜单项配置
const menuItems: MenuItem[] = [
    {
        key: 'training',
        label: '训练管理',
        type: 'group',
        children: [
            {
                key: '/sops',
                icon: <FileTextOutlined />,
                label: 'SOP 列表',
            },
            {
                key: '/monitor',
                icon: <MonitorOutlined />,
                label: '实时监控',
            },
            {
                key: '/reports',
                icon: <BarChartOutlined />,
                label: '训练报告',
            },
        ],
    },
    {
        key: 'admin',
        label: '系统管理',
        type: 'group',
        children: [
            {
                key: '/admin/faults',
                icon: <WarningOutlined />,
                label: '故障案例库',
            },
            {
                key: '/admin/seed-data',
                icon: <DatabaseOutlined />,
                label: '种子数据',
            },
            {
                key: '/admin/settings',
                icon: <SettingOutlined />,
                label: '系统设置',
            },
        ],
    },
];

interface SidebarProps {
    collapsed?: boolean;
    onCollapse?: (collapsed: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
    collapsed: controlledCollapsed,
    onCollapse
}) => {
    const [internalCollapsed, setInternalCollapsed] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const { token } = theme.useToken();

    // 支持受控和非受控模式
    const collapsed = controlledCollapsed ?? internalCollapsed;
    const setCollapsed = onCollapse ?? setInternalCollapsed;

    // 处理菜单点击
    const handleMenuClick: MenuProps['onClick'] = (info) => {
        navigate(info.key);
    };

    // 根据当前路径获取选中的菜单项
    const getSelectedKey = (): string[] => {
        const path = location.pathname;
        // 任务执行页面关联到 SOP 列表
        if (path.startsWith('/tasks')) return ['/sops'];
        if (path.startsWith('/reports')) return ['/reports'];
        return [path];
    };

    // 展开的菜单组
    const getOpenKeys = (): string[] => {
        const path = location.pathname;
        if (path.startsWith('/admin')) return ['admin'];
        return ['training'];
    };

    return (
        <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={setCollapsed}
            trigger={null}
            width={220}
            collapsedWidth={64}
            style={{
                background: token.colorBgContainer,
                borderRight: `1px solid ${token.colorBorderSecondary}`,
                overflow: 'auto',
                height: 'calc(100vh - 64px)',
                position: 'sticky',
                top: 64,
                left: 0,
            }}
        >
            <Menu
                mode="inline"
                selectedKeys={getSelectedKey()}
                defaultOpenKeys={collapsed ? [] : getOpenKeys()}
                items={menuItems}
                onClick={handleMenuClick}
                style={{
                    height: '100%',
                    borderRight: 0,
                    paddingTop: 8,
                }}
            />

            {/* 折叠按钮 */}
            <div
                style={{
                    position: 'absolute',
                    bottom: 16,
                    left: 0,
                    right: 0,
                    display: 'flex',
                    justifyContent: 'center',
                }}
            >
                <div
                    onClick={() => setCollapsed(!collapsed)}
                    style={{
                        cursor: 'pointer',
                        padding: '8px 16px',
                        borderRadius: 4,
                        background: token.colorFillSecondary,
                        color: token.colorTextSecondary,
                        transition: 'all 0.2s',
                    }}
                >
                    {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                </div>
            </div>
        </Sider>
    );
};

export default Sidebar;
