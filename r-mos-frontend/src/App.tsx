import { App as AntdApp } from 'antd'
import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import AppLayout from '@/components/Layout/AppLayout'
import { AuthProvider } from '@/components/auth/AuthContext'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { Toaster } from '@/components/ui/toaster'
import LoginPage from '@/pages/LoginPage'
import { AUTH_STORAGE_KEYS, type UserRole, useAuthStore } from '@/store/authStore'

const AdminDashboardPage = lazy(() => import('@/pages/admin/AdminDashboardPage'))
const AcceptanceDashboardPage = lazy(() => import('@/pages/admin/AcceptanceDashboardPage'))
const ApprovalQueuePage = lazy(() => import('@/pages/admin/ApprovalQueuePage'))
const FaultManagePage = lazy(() => import('@/pages/admin/FaultManagePage'))
const LLMMetricsPage = lazy(() => import('@/pages/admin/LLMMetricsPage'))
const SeedDataPage = lazy(() => import('@/pages/admin/SeedDataPage'))
const AIChatPage = lazy(() => import('@/pages/AIChatPage'))
const AssessmentStatusPage = lazy(() => import('@/pages/AssessmentStatusPage'))
const Atom01DemoPage = lazy(() => import('@/pages/Atom01DemoPage'))
const DiagnosisPage = lazy(() => import('@/pages/DiagnosisPage'))
const EvidencePage = lazy(() => import('@/pages/EvidencePage'))
const IncidentListPage = lazy(() => import('@/pages/IncidentListPage'))
const KnowledgePage = lazy(() => import('@/pages/KnowledgePage'))
const MonitorPage = lazy(() => import('@/pages/MonitorPage'))
const ReplayPage = lazy(() => import('@/pages/ReplayPage'))
const ReportPage = lazy(() => import('@/pages/ReportPage'))
const SOPListPage = lazy(() => import('@/pages/SOPListPage'))
const SOPMaintenancePage = lazy(() => import('@/pages/SOPMaintenancePage'))
const StudentSkillsPage = lazy(() => import('@/pages/StudentSkillsPage'))
const TaskExecutionPage = lazy(() => import('@/pages/TaskExecutionPage'))
const TrainingWorkbenchPage = lazy(() => import('@/pages/TrainingWorkbenchPage'))
const AgentWorkbenchPage = lazy(() => import('@/pages/agent/AgentWorkbenchPage'))
const TeachingAssignmentsPage = lazy(() => import('@/teaching/pages/TeachingAssignmentsPage'))
const TeachingAttemptPage = lazy(() => import('@/teaching/pages/TeachingAttemptPage'))
const TeachingDiagnosisPage = lazy(() => import('@/teaching/pages/TeachingDiagnosisPage'))
const TeachingEvidencePage = lazy(() => import('@/teaching/pages/TeachingEvidencePage'))
const TeacherMonitorPage = lazy(() => import('@/teaching/pages/TeacherMonitorPage'))
const TeacherStudentsPage = lazy(() => import('@/teaching/pages/TeacherStudentsPage'))

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

function RouteFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-text-muted">
      页面加载中...
    </div>
  )
}

function withSuspense(element: JSX.Element) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>
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
                  element={withSuspense(withRoles(<TrainingWorkbenchPage />, ['student']))}
                />
                <Route
                  path="student/skills"
                  element={withSuspense(withRoles(<StudentSkillsPage />, ['student']))}
                />
                <Route
                  path="workbench/teaching"
                  element={withSuspense(withRoles(<TeacherMonitorPage />, ['teacher', 'admin']))}
                />
                <Route
                  path="teacher/monitor"
                  element={<Navigate replace to="/workbench/teaching" />}
                />
                <Route
                  path="teacher/students"
                  element={withSuspense(withRoles(<TeacherStudentsPage />, ['teacher', 'admin']))}
                />
                <Route
                  path="admin/console"
                  element={withSuspense(withRoles(<AdminDashboardPage />, ['admin']))}
                />
                <Route
                  path="admin/dashboard"
                  element={<Navigate replace to="/admin/console" />}
                />

                <Route path="sops" element={withSuspense(<SOPListPage />)} />
                <Route path="knowledge" element={withSuspense(<KnowledgePage />)} />
                <Route path="ai-chat" element={withSuspense(<AIChatPage />)} />
                <Route path="monitor" element={withSuspense(<MonitorPage />)} />
                <Route path="maintenance" element={withSuspense(<SOPMaintenancePage />)} />
                <Route path="atom01" element={withSuspense(<Atom01DemoPage />)} />
                <Route
                  path="teaching/assignments"
                  element={withSuspense(withRoles(<TeachingAssignmentsPage />, ['teacher', 'admin']))}
                />
                <Route
                  path="teaching/attempts/:id"
                  element={withSuspense(withRoles(<TeachingAttemptPage />, ['teacher', 'admin']))}
                />
                <Route
                  path="teaching/attempts/:id/evidence"
                  element={withSuspense(withRoles(<TeachingEvidencePage />, ['teacher', 'admin']))}
                />
                <Route
                  path="teaching/attempts/:id/diagnosis"
                  element={withSuspense(withRoles(<TeachingDiagnosisPage />, ['teacher', 'admin']))}
                />
                <Route path="agent/workbench" element={withSuspense(<AgentWorkbenchPage />)} />
                <Route path="agent/replay" element={withSuspense(<ReplayPage />)} />
                <Route
                  path="admin/approvals"
                  element={withSuspense(withRoles(<ApprovalQueuePage />, ['admin']))}
                />
                <Route
                  path="admin/acceptance"
                  element={withSuspense(withRoles(<AcceptanceDashboardPage />, ['admin']))}
                />
                <Route
                  path="admin/llm-metrics"
                  element={withSuspense(withRoles(<LLMMetricsPage />, ['admin']))}
                />
                <Route
                  path="admin/faults"
                  element={withSuspense(withRoles(<FaultManagePage />, ['admin']))}
                />
                <Route
                  path="admin/seed-data"
                  element={withSuspense(withRoles(<SeedDataPage />, ['admin']))}
                />
                <Route path="incidents" element={withSuspense(<IncidentListPage />)} />
                <Route path="evidence" element={withSuspense(<EvidencePage />)} />
                <Route path="assessments" element={withSuspense(<AssessmentStatusPage />)} />
                <Route path="reports" element={withSuspense(<ReportPage />)} />
                <Route path="reports/:taskId" element={withSuspense(<ReportPage />)} />
                <Route path="diagnosis/:taskId" element={withSuspense(<DiagnosisPage />)} />
                <Route path="tasks/:taskId" element={withSuspense(<TaskExecutionPage />)} />
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
