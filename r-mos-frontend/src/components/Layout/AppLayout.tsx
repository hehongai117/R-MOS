import {
  Bot,
  LogOut,
  Settings,
  Sparkles,
} from 'lucide-react'
import { useEffect } from 'react'
import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { GlobalAIChat } from '@/components/AIAssistant/GlobalAIChat'
import { LAYOUT_CONFIG, type NavItem, type NavGroup } from '@/config/nav'
import { BRAND_NAME } from '@/config/brand'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { type UserRole, useAuthStore } from '@/store/authStore'
import { useRobotContextStore } from '@/store/robotContextStore'


function getDisplayName(fullName?: string, email?: string) {
  return fullName?.trim() || email || '未命名用户'
}

function getAvatarFallback(fullName?: string, email?: string) {
  const source = getDisplayName(fullName, email)
  return source.slice(0, 2).toUpperCase()
}

function SidebarNavItem({ icon: Icon, label, to }: NavItem) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center gap-3 rounded-md px-3 py-2 text-[13px] transition-colors duration-base ease-base',
          isActive
            ? 'bg-primary-muted text-primary'
            : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary',
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={cn(
              'absolute left-0 top-2 h-5 w-[3px] rounded-r-full transition-opacity',
              isActive ? 'bg-primary opacity-100' : 'opacity-0',
            )}
          />
          <Icon className="h-4 w-4 shrink-0" />
          <span className="truncate">{label}</span>
        </>
      )}
    </NavLink>
  )
}

function SidebarNavGroup({ group, isFirst }: { group: NavGroup; isFirst: boolean }) {
  return (
    <div className={cn(!isFirst && 'mt-4')}>
      <div className="mb-1.5 px-3 text-[11px] font-medium uppercase tracking-wider text-text-muted">
        {group.label}
      </div>
      <div className="space-y-0.5">
        {group.items.map((item) => (
          <SidebarNavItem key={item.to} {...item} />
        ))}
      </div>
    </div>
  )
}

function RoleLayoutShell({
  role,
  fullName,
  email,
}: {
  role: UserRole
  fullName?: string
  email?: string
}) {
  const logout = useAuthStore((state) => state.logout)
  const navigate = useNavigate()
  const config = LAYOUT_CONFIG[role]
  const displayName = getDisplayName(fullName, email)
  const { currentRobot, availableRobots, setCurrentRobot } = useRobotContextStore()

  return (
    <div className="flex min-h-screen bg-bg-base text-text-primary">
      <aside className="fixed inset-y-0 left-0 flex w-[220px] flex-col border-r border-border-subtle bg-bg-surface">
        <div className="flex h-14 items-center gap-3 border-b border-border-subtle px-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/30 bg-primary-muted text-primary shadow-sm">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate font-mono text-sm text-text-primary">{BRAND_NAME}</p>
            <p className="truncate text-[11px] uppercase tracking-[0.24em] text-text-muted">
              Robotics OS
            </p>
          </div>
        </div>

        <ScrollArea className="flex-1 px-3 py-3">
          <nav>
            {config.navGroups.map((group, idx) => (
              <SidebarNavGroup key={group.label} group={group} isFirst={idx === 0} />
            ))}
          </nav>
        </ScrollArea>

        <Separator />

        <div className="px-3 py-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors duration-base ease-base hover:bg-bg-elevated">
                <Avatar className="h-9 w-9">
                  <AvatarFallback>{getAvatarFallback(fullName, email)}</AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm text-text-primary">{displayName}</div>
                  <div className="mt-1">
                    <Badge variant={config.badgeVariant}>{config.badgeLabel}</Badge>
                  </div>
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuLabel className="space-y-1">
                <div className="text-sm text-text-primary">{displayName}</div>
                <div className="text-xs text-text-secondary">{email ?? '未绑定邮箱'}</div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/settings')}>
                <Settings className="mr-2 h-4 w-4" />
                个人设置
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => void logout()}>
                <LogOut className="mr-2 h-4 w-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      <main className="ml-[220px] flex-1 overflow-auto">
        {/* 有多台机器人时显示顶部机器人切换栏 */}
        {availableRobots.length > 1 && (
          <div className="sticky top-0 z-10 flex items-center gap-3 border-b border-border-subtle bg-bg-surface/95 px-6 py-2 backdrop-blur">
            <Bot className="h-4 w-4 text-text-muted" />
            <span className="text-xs text-text-secondary">当前机器人:</span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 rounded-md border border-border-subtle px-3 py-1 text-xs transition-colors hover:bg-bg-elevated">
                  <span>{currentRobot ? `${currentRobot.brand} ${currentRobot.model_name}` : '请选择机器人'}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                {availableRobots.map((r) => (
                  <DropdownMenuItem
                    key={r.id}
                    onClick={() => setCurrentRobot(r)}
                    className={cn(r.id === currentRobot?.id && 'bg-primary-muted text-primary')}
                  >
                    {r.brand} {r.model_name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
        <div className="mx-auto min-h-[calc(100vh-3rem)] max-w-[1600px] p-6">
          <Outlet />
        </div>
      </main>
      <GlobalAIChat />
    </div>
  )
}

function AppLayout() {
  const user = useAuthStore((state) => state.user)
  const fetchAvailableRobots = useRobotContextStore((s) => s.fetchAvailableRobots)
  const fetchTeacherRobots = useRobotContextStore((s) => s.fetchTeacherRobots)

  // 在 Layout 级别加载机器人上下文，确保所有子页面都能获取 currentRobot
  useEffect(() => {
    if (!user?.user_id) return
    if (user.role === 'student') {
      fetchAvailableRobots(user.user_id)
    } else if (user.role === 'teacher' || user.role === 'admin') {
      fetchTeacherRobots()
    }
  }, [user?.user_id, user?.role, fetchAvailableRobots, fetchTeacherRobots])

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <RoleLayoutShell
      role={user.role}
      fullName={user.full_name}
      email={user.email}
    />
  )
}

export default AppLayout
