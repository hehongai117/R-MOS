import { App as AntdApp } from 'antd'
import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import AppLayout from '@/components/Layout/AppLayout'
import { AuthProvider } from '@/components/auth/AuthContext'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { Toaster } from '@/components/ui/toaster'
import { PageSkeleton } from '@/components/ui/skeleton'
import LoginPage from '@/pages/LoginPage'
const RegisterPage = lazy(() => import('@/pages/RegisterPage'))
import { AUTH_STORAGE_KEYS, type UserRole, useAuthStore } from '@/store/authStore'

const AdminDashboardPage = lazy(() => import('@/pages/admin/AdminDashboardPage'))
const UserSettingsPage = lazy(() => import('@/pages/UserSettingsPage'))
const Atom01DemoPage = lazy(() => import('@/pages/Atom01DemoPage'))
const KnowledgePage = lazy(() => import('@/pages/KnowledgePage'))
const MonitorPage = lazy(() => import('@/pages/MonitorPage'))
const MyTasksPage = lazy(() => import('@/pages/MyTasksPage'))
const ReportPage = lazy(() => import('@/pages/ReportPage'))
const ScenarioPickerPage = lazy(() => import('@/pages/ScenarioPickerPage'))
const SOPListPage = lazy(() => import('@/pages/SOPListPage'))
const SOPMaintenancePage = lazy(() => import('@/pages/SOPMaintenancePage'))
const StudentSkillsPage = lazy(() => import('@/pages/StudentSkillsPage'))
const AgentWorkbenchPage = lazy(() => import('@/pages/agent/AgentWorkbenchPage'))
const TeachingAssignmentsPage = lazy(() => import('@/teaching/pages/TeachingAssignmentsPage'))
const TeachingAttemptPage = lazy(() => import('@/teaching/pages/TeachingAttemptPage'))
const TeachingDiagnosisPage = lazy(() => import('@/teaching/pages/TeachingDiagnosisPage'))
const TeachingEvidencePage = lazy(() => import('@/teaching/pages/TeachingEvidencePage'))
const TeacherMonitorPage = lazy(() => import('@/teaching/pages/TeacherMonitorPage'))
const TeacherStudentsPage = lazy(() => import('@/teaching/pages/TeacherStudentsPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))

function DefaultRouteRedirect() {
  const defaultRoute =
    useAuthStore((state) => state.defaultRoute) ??
    localStorage.getItem(AUTH_STORAGE_KEYS.defaultRoute) ??
    '/dashboard'

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
    <div className="p-6">
      <PageSkeleton />
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
            <Route path="/register" element={withSuspense(<RegisterPage />)} />

            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<DefaultRouteRedirect />} />
                <Route
                  path="dashboard"
                  element={withSuspense(withRoles(<DashboardPage />, ['student']))}
                />

                <Route
                  path="my-tasks"
                  element={withSuspense(withRoles(<MyTasksPage />, ['student']))}
                />
                <Route
                  path="scenarios"
                  element={withSuspense(withRoles(<ScenarioPickerPage />, ['student']))}
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
                  path="teacher/students"
                  element={withSuspense(withRoles(<TeacherStudentsPage />, ['teacher', 'admin']))}
                />
                <Route
                  path="admin/console"
                  element={withSuspense(withRoles(<AdminDashboardPage />, ['admin']))}
                />

                <Route path="sops" element={withSuspense(withRoles(<SOPListPage />, ['teacher', 'admin']))} />
                <Route path="knowledge" element={withSuspense(withRoles(<KnowledgePage />, ['teacher', 'admin']))} />
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
                <Route path="settings" element={withSuspense(<UserSettingsPage />)} />
                <Route path="reports" element={withSuspense(<ReportPage />)} />
                <Route path="reports/:taskId" element={withSuspense(<ReportPage />)} />
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
