import { App as AntdApp } from 'antd'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import AppLayout from '@/components/Layout/AppLayout'
import { AuthProvider } from '@/components/auth/AuthContext'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { Toaster } from '@/components/ui/toaster'
import AdminDashboardPage from '@/pages/admin/AdminDashboardPage'
import AcceptanceDashboardPage from '@/pages/admin/AcceptanceDashboardPage'
import ApprovalQueuePage from '@/pages/admin/ApprovalQueuePage'
import FaultManagePage from '@/pages/admin/FaultManagePage'
import LLMMetricsPage from '@/pages/admin/LLMMetricsPage'
import SeedDataPage from '@/pages/admin/SeedDataPage'
import AIChatPage from '@/pages/AIChatPage'
import AssessmentStatusPage from '@/pages/AssessmentStatusPage'
import Atom01DemoPage from '@/pages/Atom01DemoPage'
import DiagnosisPage from '@/pages/DiagnosisPage'
import EvidencePage from '@/pages/EvidencePage'
import IncidentListPage from '@/pages/IncidentListPage'
import KnowledgePage from '@/pages/KnowledgePage'
import LoginPage from '@/pages/LoginPage'
import MonitorPage from '@/pages/MonitorPage'
import ReplayPage from '@/pages/ReplayPage'
import ReportPage from '@/pages/ReportPage'
import SOPListPage from '@/pages/SOPListPage'
import SOPMaintenancePage from '@/pages/SOPMaintenancePage'
import StudentSkillsPage from '@/pages/StudentSkillsPage'
import TaskExecutionPage from '@/pages/TaskExecutionPage'
import TrainingWorkbenchPage from '@/pages/TrainingWorkbenchPage'
import AgentWorkbenchPage from '@/pages/agent/AgentWorkbenchPage'
import { AUTH_STORAGE_KEYS, type UserRole, useAuthStore } from '@/store/authStore'
import TeachingAssignmentsPage from '@/teaching/pages/TeachingAssignmentsPage'
import TeachingAttemptPage from '@/teaching/pages/TeachingAttemptPage'
import TeachingDiagnosisPage from '@/teaching/pages/TeachingDiagnosisPage'
import TeachingEvidencePage from '@/teaching/pages/TeachingEvidencePage'
import TeacherMonitorPage from '@/teaching/pages/TeacherMonitorPage'
import TeacherStudentsPage from '@/teaching/pages/TeacherStudentsPage'

function DefaultRouteRedirect() {
  const defaultRoute =
    useAuthStore((state) => state.defaultRoute) ??
    localStorage.getItem(AUTH_STORAGE_KEYS.defaultRoute) ??
    '/login'

  return <Navigate replace to={defaultRoute} />
}

function withRoles(element: JSX.Element, allowedRoles?: UserRole[]) {
  if (!allowedRoles) {
    return element
  }

  return <ProtectedRoute allowedRoles={allowedRoles}>{element}</ProtectedRoute>
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AntdApp>
          <Toaster />
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<DefaultRouteRedirect />} />

                <Route
                  path="workbench/training"
                  element={withRoles(<TrainingWorkbenchPage />, ['student'])}
                />
                <Route
                  path="student/skills"
                  element={withRoles(<StudentSkillsPage />, ['student'])}
                />
                <Route
                  path="workbench/teaching"
                  element={withRoles(<TeacherMonitorPage />, ['teacher', 'admin'])}
                />
                <Route
                  path="teacher/monitor"
                  element={<Navigate replace to="/workbench/teaching" />}
                />
                <Route
                  path="teacher/students"
                  element={withRoles(<TeacherStudentsPage />, ['teacher', 'admin'])}
                />
                <Route
                  path="admin/console"
                  element={withRoles(<AdminDashboardPage />, ['admin'])}
                />
                <Route
                  path="admin/dashboard"
                  element={<Navigate replace to="/admin/console" />}
                />

                <Route path="sops" element={<SOPListPage />} />
                <Route path="knowledge" element={<KnowledgePage />} />
                <Route path="ai-chat" element={<AIChatPage />} />
                <Route path="monitor" element={<MonitorPage />} />
                <Route path="maintenance" element={<SOPMaintenancePage />} />
                <Route path="atom01" element={<Atom01DemoPage />} />
                <Route
                  path="teaching/assignments"
                  element={withRoles(<TeachingAssignmentsPage />, ['teacher', 'admin'])}
                />
                <Route
                  path="teaching/attempts/:id"
                  element={withRoles(<TeachingAttemptPage />, ['teacher', 'admin'])}
                />
                <Route
                  path="teaching/attempts/:id/evidence"
                  element={withRoles(<TeachingEvidencePage />, ['teacher', 'admin'])}
                />
                <Route
                  path="teaching/attempts/:id/diagnosis"
                  element={withRoles(<TeachingDiagnosisPage />, ['teacher', 'admin'])}
                />
                <Route path="agent/workbench" element={<AgentWorkbenchPage />} />
                <Route path="agent/replay" element={<ReplayPage />} />
                <Route
                  path="admin/approvals"
                  element={withRoles(<ApprovalQueuePage />, ['admin'])}
                />
                <Route
                  path="admin/acceptance"
                  element={withRoles(<AcceptanceDashboardPage />, ['admin'])}
                />
                <Route
                  path="admin/llm-metrics"
                  element={withRoles(<LLMMetricsPage />, ['admin'])}
                />
                <Route
                  path="admin/faults"
                  element={withRoles(<FaultManagePage />, ['admin'])}
                />
                <Route
                  path="admin/seed-data"
                  element={withRoles(<SeedDataPage />, ['admin'])}
                />
                <Route path="incidents" element={<IncidentListPage />} />
                <Route path="evidence" element={<EvidencePage />} />
                <Route path="assessments" element={<AssessmentStatusPage />} />
                <Route path="reports" element={<ReportPage />} />
                <Route path="reports/:taskId" element={<ReportPage />} />
                <Route path="diagnosis/:taskId" element={<DiagnosisPage />} />
                <Route path="tasks/:taskId" element={<TaskExecutionPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </AntdApp>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
