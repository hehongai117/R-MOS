/**
 * R-MOS 根组件 + 路由配置（V2.3 增强 - Dark Mode Pro）
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppLayout from './components/Layout/AppLayout'
import HomePage from './pages/HomePage'
import SOPListPage from './pages/SOPListPage'
import TaskExecutionPage from './pages/TaskExecutionPage'
import MonitorPage from './pages/MonitorPage'
import ReportPage from './pages/ReportPage'
import FaultManagePage from './pages/admin/FaultManagePage'
import SeedDataPage from './pages/admin/SeedDataPage'
import IncidentListPage from './pages/IncidentListPage'
import EvidencePage from './pages/EvidencePage'
import AssessmentStatusPage from './pages/AssessmentStatusPage'
import Atom01DemoPage from './pages/Atom01DemoPage'
import SOPMaintenancePage from './pages/SOPMaintenancePage'
import { darkTheme } from './styles/theme'
import './styles/index.css'

function App() {
    return (
        <ConfigProvider
            theme={darkTheme}
            locale={zhCN}
        >
            <AntdApp>
                <BrowserRouter>
                    <Routes>
                        <Route path="/" element={<AppLayout />}>
                            {/* 默认显示首页 */}
                            <Route index element={<HomePage />} />

                            {/* 核心页面 */}
                            <Route path="sops" element={<SOPListPage />} />
                            <Route path="tasks/:taskId" element={<TaskExecutionPage />} />
                            <Route path="monitor" element={<MonitorPage />} />
                            <Route path="reports" element={<ReportPage />} />
                            <Route path="reports/:taskId" element={<ReportPage />} />
                            <Route path="incidents" element={<IncidentListPage />} />
                            <Route path="evidence" element={<EvidencePage />} />
                            <Route path="assessments" element={<AssessmentStatusPage />} />

                            {/* Atom01 3D 展示 */}
                            <Route path="atom01" element={<Atom01DemoPage />} />

                            {/* SOP 维保系统 */}
                            <Route path="maintenance" element={<SOPMaintenancePage />} />

                            {/* 管理页面 */}
                            <Route path="admin/faults" element={<FaultManagePage />} />
                            <Route path="admin/seed-data" element={<SeedDataPage />} />
                        </Route>
                    </Routes>
                </BrowserRouter>
            </AntdApp>
        </ConfigProvider>
    )
}

export default App

