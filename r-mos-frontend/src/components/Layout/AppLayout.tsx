import {
  Activity,
  AlertTriangle,
  BarChart2,
  BarChart3,
  BookOpen,
  Bot,
  Boxes,
  Brain,
  CheckSquare,
  ClipboardList,
  Cpu,
  Database,
  Dumbbell,
  FileSearch,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Monitor,
  PlayCircle,
  Settings,
  ShieldCheck,
  Sparkles,
  ToggleRight,
  Users,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom'

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

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

interface NavGroup {
  label: string
  items: NavItem[]
}

interface LayoutConfig {
  badgeLabel: string
  badgeVariant: 'default' | 'success' | 'destructive'
  navGroups: NavGroup[]
}

const STUDENT_NAV: NavGroup[] = [
  {
    label: '工作台',
    items: [
      { label: '训练工作台', to: '/workbench/training', icon: Dumbbell },
      { label: 'AI 工作台', to: '/agent/workbench', icon: Bot },
      { label: 'ATOM01 维保工作台', to: '/workbench/atom01-maintenance', icon: Boxes },
      { label: 'SOP 工作台', to: '/maintenance', icon: Wrench },
    ],
  },
  {
    label: '工具',
    items: [
      { label: '3D 展示', to: '/atom01', icon: Boxes },
      { label: '实时监控', to: '/monitor', icon: Activity },
    ],
  },
  {
    label: '记录与资源',
    items: [
      { label: '我的技能', to: '/student/skills', icon: BarChart3 },
      { label: '任务报告', to: '/reports', icon: FileText },
      { label: '执行回放', to: '/agent/replay', icon: PlayCircle },
      { label: '知识库', to: '/knowledge', icon: BookOpen },
      { label: 'AI 助手', to: '/ai-chat', icon: MessageSquare },
    ],
  },
]

const TEACHER_NAV: NavGroup[] = [
  {
    label: '工作台',
    items: [
      { label: '班级监控台', to: '/workbench/teaching', icon: Monitor },
      { label: 'ATOM01 维保工作台', to: '/workbench/atom01-maintenance', icon: Boxes },
      { label: 'SOP 工作台', to: '/maintenance', icon: Wrench },
    ],
  },
  {
    label: '教学管理',
    items: [
      { label: '作业管理', to: '/teaching/assignments', icon: ClipboardList },
      { label: '学员档案', to: '/teacher/students', icon: Users },
    ],
  },
  {
    label: 'SOP & 工具',
    items: [
      { label: 'SOP 管理', to: '/sops', icon: FileText },
      { label: '3D 展示', to: '/atom01', icon: Boxes },
    ],
  },
  {
    label: '监控与审核',
    items: [
      { label: '实时监控', to: '/monitor', icon: Activity },
      { label: '事件列表', to: '/incidents', icon: AlertTriangle },
      { label: '证据查看', to: '/evidence', icon: FileSearch },
      { label: '评估状态', to: '/assessments', icon: ShieldCheck },
    ],
  },
  {
    label: '记录与资源',
    items: [
      { label: '任务报告', to: '/reports', icon: BarChart3 },
      { label: '执行回放', to: '/agent/replay', icon: PlayCircle },
      { label: '知识库', to: '/knowledge', icon: BookOpen },
      { label: 'AI 助手', to: '/ai-chat', icon: MessageSquare },
    ],
  },
]

const ADMIN_NAV: NavGroup[] = [
  {
    label: '概览',
    items: [
      { label: '系统概览', to: '/admin/console', icon: LayoutDashboard },
    ],
  },
  {
    label: '工作台',
    items: [
      { label: '班级监控台', to: '/workbench/teaching', icon: Monitor },
      { label: 'ATOM01 维保工作台', to: '/workbench/atom01-maintenance', icon: Boxes },
      { label: 'SOP 工作台', to: '/maintenance', icon: Wrench },
    ],
  },
  {
    label: '教学管理',
    items: [
      { label: '作业管理', to: '/teaching/assignments', icon: ClipboardList },
      { label: '学员档案', to: '/teacher/students', icon: Users },
    ],
  },
  {
    label: 'SOP & 工具',
    items: [
      { label: 'SOP 管理', to: '/sops', icon: FileText },
      { label: '3D 展示', to: '/atom01', icon: Boxes },
    ],
  },
  {
    label: '监控与审核',
    items: [
      { label: '实时监控', to: '/monitor', icon: Activity },
      { label: '事件列表', to: '/incidents', icon: AlertTriangle },
      { label: '证据查看', to: '/evidence', icon: FileSearch },
      { label: '评估状态', to: '/assessments', icon: ShieldCheck },
      { label: '信念追踪', to: '/belief-tracker', icon: Brain },
    ],
  },
  {
    label: '平台管理',
    items: [
      { label: '审批队列', to: '/admin/approvals', icon: CheckSquare },
      { label: '补偿方案', to: '/admin/compensation', icon: Wrench },
      { label: 'Feature Flag', to: '/admin/features', icon: ToggleRight },
      { label: '验收看板', to: '/admin/acceptance', icon: BarChart2 },
      { label: 'LLM 指标', to: '/admin/llm-metrics', icon: Cpu },
      { label: '故障管理', to: '/admin/faults', icon: AlertTriangle },
      { label: '数据管理', to: '/admin/seed-data', icon: Database },
      { label: '知识库', to: '/knowledge', icon: BookOpen },
      { label: 'AI 助手', to: '/ai-chat', icon: MessageSquare },
    ],
  },
]

const LAYOUT_CONFIG: Record<UserRole, LayoutConfig> = {
  student: {
    badgeLabel: '学员',
    badgeVariant: 'default',
    navGroups: STUDENT_NAV,
  },
  teacher: {
    badgeLabel: '教师',
    badgeVariant: 'success',
    navGroups: TEACHER_NAV,
  },
  admin: {
    badgeLabel: '管理员',
    badgeVariant: 'destructive',
    navGroups: ADMIN_NAV,
  },
}

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

  return (
    <div className="flex min-h-screen bg-bg-base text-text-primary">
      <aside className="fixed inset-y-0 left-0 flex w-[220px] flex-col border-r border-border-subtle bg-bg-surface">
        <div className="flex h-14 items-center gap-3 border-b border-border-subtle px-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/30 bg-primary-muted text-primary shadow-sm">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate font-mono text-sm text-text-primary">R-MOS</p>
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

      <main className="ml-[220px] flex-1 overflow-auto p-6">
        <div className="mx-auto min-h-[calc(100vh-3rem)] max-w-[1600px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function AppLayout() {
  const user = useAuthStore((state) => state.user)

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
