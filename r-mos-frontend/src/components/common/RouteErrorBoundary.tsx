/**
 * RouteErrorBoundary — 路由级错误边界（Phase 4 健壮性）
 *
 * 薄封装既有 ErrorBoundary：
 * - 以 useLocation().pathname 作为 React key，导航到新路由时自动清除错误态，
 *   无需用户手动重试就能继续使用其他页面。
 * - 提供页面级友好文案（区别于 3D 视图的 Viewer3DErrorBoundary）。
 * - 挂载在 AppLayout <Outlet /> 外层，页面崩溃时保留侧边栏/导航，
 *   仅内容区降级；无布局路由（登录/注册）在 App.tsx 中各自包裹。
 */
import React, { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

import { ErrorBoundary } from './ErrorBoundary'

interface Props {
  children: ReactNode
}

export const RouteErrorBoundary: React.FC<Props> = ({ children }) => {
  const { pathname } = useLocation()
  return (
    <ErrorBoundary
      key={pathname}
      fallbackTitle="页面出错了"
      fallbackMessage="当前页面遇到了一个错误，请点击重试或返回其他页面继续使用。"
    >
      {children}
    </ErrorBoundary>
  )
}

export default RouteErrorBoundary
