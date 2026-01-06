/**
 * R-MOS 根组件 + 路由配置
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './components/Layout/AppLayout'
import HomePage from './pages/HomePage'
import SOPListPage from './pages/SOPListPage'
import TaskExecutionPage from './pages/TaskExecutionPage'
import MonitorPage from './pages/MonitorPage'
import ReportPage from './pages/ReportPage'
import FaultManagePage from './pages/admin/FaultManagePage'
import SeedDataPage from './pages/admin/SeedDataPage'

function App() {
    return (
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

                    {/* 管理页面 */}
                    <Route path="admin/faults" element={<FaultManagePage />} />
                    <Route path="admin/seed-data" element={<SeedDataPage />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}

export default App
