import { type ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { AUTH_STORAGE_KEYS, type UserRole, useAuthStore } from '@/store/authStore'

export interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
  children?: ReactNode
}

export function getStoredDefaultRoute() {
  return localStorage.getItem(AUTH_STORAGE_KEYS.defaultRoute) ?? '/login'
}

export function ProtectedRoute({ allowedRoles, children }: ProtectedRouteProps) {
  const location = useLocation()
  const { accessToken, isInitialized, user } = useAuthStore((state) => ({
    accessToken: state.accessToken,
    isInitialized: state.isInitialized,
    user: state.user,
  }))

  if (!isInitialized) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-base text-sm text-text-secondary">
        正在校验登录状态...
      </div>
    )
  }

  if (!accessToken || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  // 教师未完成 onboarding 时，强制跳转机器人选择页
  if (
    user.role === 'teacher' &&
    user.onboarding_completed === false &&
    location.pathname !== '/onboarding/robots'
  ) {
    return <Navigate to="/onboarding/robots" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={getStoredDefaultRoute()} replace />
  }

  return children ? <>{children}</> : <Outlet />
}

export default ProtectedRoute
