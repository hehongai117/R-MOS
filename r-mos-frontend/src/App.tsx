import { App as AntdApp } from 'antd'
import { Suspense, lazy, useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import AppLayout from '@/components/Layout/AppLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { RouteErrorBoundary } from '@/components/common/RouteErrorBoundary'
import { Toaster } from '@/components/ui/toaster'
import { PageSkeleton } from '@/components/ui/skeleton'
import LoginPage from '@/pages/LoginPage'
const RegisterPage = lazy(() => import('@/pages/RegisterPage'))
import { AUTH_STORAGE_KEYS, type UserRole, useAuthStore } from '@/store/authStore'
import { getAllowedRoles } from '@/config/routes'

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
const SharedRobotsPage = lazy(() => import('@/pages/SharedRobotsPage'))
const OnboardingRobotsPage = lazy(() => import('./pages/OnboardingRobotsPage'))

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
  const initFromStorage = useAuthStore((state) => state.initFromStorage)
  useEffect(() => { void initFromStorage() }, [initFromStorage])

  return (
      <BrowserRouter>
        <AntdApp>
          <Toaster />
          <Routes>
            <Route path="/login" element={<RouteErrorBoundary><LoginPage /></RouteErrorBoundary>} />
            <Route path="/register" element={<RouteErrorBoundary>{withSuspense(<RegisterPage />)}</RouteErrorBoundary>} />

            <Route element={<ProtectedRoute />}>
              <Route path="onboarding/robots" element={<RouteErrorBoundary>{withSuspense(<OnboardingRobotsPage />)}</RouteErrorBoundary>} />
              <Route path="/" element={<AppLayout />}>
                <Route index element={<DefaultRouteRedirect />} />
                <Route
                  path="dashboard"
                  element={withSuspense(withRoles(<DashboardPage />, getAllowedRoles('dashboard')))}
                />

                <Route
                  path="my-tasks"
                  element={withSuspense(withRoles(<MyTasksPage />, getAllowedRoles('my-tasks')))}
                />
                <Route
                  path="scenarios"
                  element={withSuspense(withRoles(<ScenarioPickerPage />, getAllowedRoles('scenarios')))}
                />
                <Route
                  path="student/skills"
                  element={withSuspense(withRoles(<StudentSkillsPage />, getAllowedRoles('student/skills')))}
                />
                <Route
                  path="workbench/teaching"
                  element={withSuspense(withRoles(<TeacherMonitorPage />, getAllowedRoles('workbench/teaching')))}
                />
                <Route
                  path="teacher/students"
                  element={withSuspense(withRoles(<TeacherStudentsPage />, getAllowedRoles('teacher/students')))}
                />
                <Route
                  path="admin/console"
                  element={withSuspense(withRoles(<AdminDashboardPage />, getAllowedRoles('admin/console')))}
                />

                <Route path="sops" element={withSuspense(withRoles(<SOPListPage />, getAllowedRoles('sops')))} />
                <Route path="knowledge" element={withSuspense(withRoles(<KnowledgePage />, getAllowedRoles('knowledge')))} />
                <Route path="shared-robots" element={withSuspense(withRoles(<SharedRobotsPage />, getAllowedRoles('shared-robots')))} />
                <Route path="monitor" element={withSuspense(withRoles(<MonitorPage />, getAllowedRoles('monitor')))} />
                <Route path="maintenance" element={withSuspense(withRoles(<SOPMaintenancePage />, getAllowedRoles('maintenance')))} />
                <Route path="3d-viewer" element={withSuspense(withRoles(<Atom01DemoPage />, getAllowedRoles('3d-viewer')))} />
                <Route
                  path="teaching/assignments"
                  element={withSuspense(withRoles(<TeachingAssignmentsPage />, getAllowedRoles('teaching/assignments')))}
                />
                <Route
                  path="teaching/attempts/:id"
                  element={withSuspense(withRoles(<TeachingAttemptPage />, getAllowedRoles('teaching/attempts/:id')))}
                />
                <Route
                  path="teaching/attempts/:id/evidence"
                  element={withSuspense(withRoles(<TeachingEvidencePage />, getAllowedRoles('teaching/attempts/:id/evidence')))}
                />
                <Route
                  path="teaching/attempts/:id/diagnosis"
                  element={withSuspense(withRoles(<TeachingDiagnosisPage />, getAllowedRoles('teaching/attempts/:id/diagnosis')))}
                />
                <Route path="agent/workbench" element={withSuspense(withRoles(<AgentWorkbenchPage />, getAllowedRoles('agent/workbench')))} />
                <Route path="settings" element={withSuspense(withRoles(<UserSettingsPage />, getAllowedRoles('settings')))} />
                <Route path="reports" element={withSuspense(withRoles(<ReportPage />, getAllowedRoles('reports')))} />
                <Route path="reports/:taskId" element={withSuspense(withRoles(<ReportPage />, getAllowedRoles('reports/:taskId')))} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </AntdApp>
      </BrowserRouter>
  )
}

export default App
