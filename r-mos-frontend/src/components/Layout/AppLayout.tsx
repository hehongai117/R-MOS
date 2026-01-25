/**
 * R-MOS 应用主布局组件
 * 包含顶部导航栏、左侧菜单和内容区域
 */
import { Layout, Menu, theme } from 'antd'
import {
    DashboardOutlined,
    FileTextOutlined,
    MonitorOutlined,
    WarningOutlined,
    DatabaseOutlined,
    HomeOutlined,
    AlertOutlined,
    FolderOpenOutlined,
    AuditOutlined,
    ToolOutlined,
    RobotOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout

// 侧边栏菜单项
const menuItems = [
    {
        key: '/',
        icon: <HomeOutlined />,
        label: '首页',
    },
    {
        key: '/maintenance',
        icon: <ToolOutlined />,
        label: 'SOP 维保系统',
    },
    {
        key: '/atom01',
        icon: <RobotOutlined />,
        label: '机器人演示',
    },
    {
        key: '/sops',
        icon: <FileTextOutlined />,
        label: 'SOP列表',
    },
    {
        key: '/monitor',
        icon: <MonitorOutlined />,
        label: '实时监控',
    },
    {
        key: '/incidents',
        icon: <AlertOutlined />,
        label: '事件列表',
    },
    {
        key: '/evidence',
        icon: <FolderOpenOutlined />,
        label: '证据包',
    },
    {
        key: '/assessments',
        icon: <AuditOutlined />,
        label: '评估状态',
    },
    {
        key: '/admin/faults',
        icon: <WarningOutlined />,
        label: '故障管理',
    },
    {
        key: '/admin/seed-data',
        icon: <DatabaseOutlined />,
        label: '种子数据',
    },
]

function AppLayout() {
    const navigate = useNavigate()
    const location = useLocation()
    const {
        token: { colorBgContainer, borderRadiusLG },
    } = theme.useToken()

    // 处理菜单点击
    const handleMenuClick = (info: { key: string }) => {
        navigate(info.key)
    }

    // 根据当前路径获取选中的菜单项
    const getSelectedKey = () => {
        const path = location.pathname
        if (path.startsWith('/tasks')) return '/sops'
        if (path.startsWith('/reports')) return '/sops'
        return path
    }

    return (
        <Layout style={{ minHeight: '100vh' }}>
            {/* 顶部导航栏 */}
            <Header
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0 24px',
                    background: '#001529',
                }}
            >
                <div
                    style={{
                        color: '#fff',
                        fontSize: '18px',
                        fontWeight: 'bold',
                    }}
                >
                    <DashboardOutlined style={{ marginRight: 8 }} />
                    R-MOS 机器人维护操作系统
                </div>
            </Header>

            <Layout>
                {/* 左侧菜单 */}
                <Sider
                    width={200}
                    style={{ background: colorBgContainer }}
                    breakpoint="lg"
                    collapsedWidth={80}
                >
                    <Menu
                        mode="inline"
                        selectedKeys={[getSelectedKey()]}
                        style={{ height: '100%', borderRight: 0 }}
                        items={menuItems}
                        onClick={handleMenuClick}
                    />
                </Sider>

                {/* 主内容区域 */}
                <Layout style={{ padding: '16px 24px' }}>
                    <Content
                        style={{
                            padding: 24,
                            margin: 0,
                            minHeight: 280,
                            background: colorBgContainer,
                            borderRadius: borderRadiusLG,
                        }}
                    >
                        <Outlet />
                    </Content>
                </Layout>
            </Layout>
        </Layout>
    )
}

export default AppLayout
