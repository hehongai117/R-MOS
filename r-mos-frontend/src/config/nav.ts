import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  Boxes,
  ClipboardList,
  Dumbbell,
  FileText,
  LayoutDashboard,
  Monitor,
  Users,
  Wrench,
  type LucideIcon,
} from 'lucide-react'

import { type UserRole } from '@/store/authStore'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

export interface LayoutConfig {
  badgeLabel: string
  badgeVariant: 'default' | 'success' | 'destructive'
  navGroups: NavGroup[]
}

const STUDENT_NAV: NavGroup[] = [
  {
    label: '练习中心',
    items: [
      { label: '学习进度', to: '/dashboard', icon: BarChart3 },
      { label: '我的任务', to: '/my-tasks', icon: ClipboardList },
      { label: '自主练习', to: '/scenarios', icon: Dumbbell },
    ],
  },
  {
    label: '维保操作',
    items: [
      { label: '实时监控', to: '/monitor', icon: Activity },
      { label: '维保练习', to: '/maintenance', icon: Wrench },
    ],
  },
  {
    label: '学习成长',
    items: [
      { label: '维保报告', to: '/reports', icon: FileText },
      { label: '我的技能', to: '/student/skills', icon: BarChart3 },
      { label: '3D 展示', to: '/3d-viewer', icon: Boxes },
    ],
  },
  {
    label: '进阶工具',
    items: [
      { label: 'AI 诊断工作台', to: '/agent/workbench', icon: Bot },
    ],
  },
]

const TEACHER_NAV: NavGroup[] = [
  {
    label: '教学管理',
    items: [
      { label: '班级监控台', to: '/workbench/teaching', icon: Monitor },
      { label: '作业管理', to: '/teaching/assignments', icon: ClipboardList },
      { label: '学员档案', to: '/teacher/students', icon: Users },
    ],
  },
  {
    label: 'SOP & 工具',
    items: [
      { label: 'SOP 管理', to: '/sops', icon: FileText },
      { label: '3D 展示', to: '/3d-viewer', icon: Boxes },
      { label: '实时监控', to: '/monitor', icon: Activity },
    ],
  },
  {
    label: '记录',
    items: [
      { label: '维保报告', to: '/reports', icon: BarChart3 },
      { label: '知识库', to: '/knowledge', icon: BookOpen },
      { label: '共享机器人库', to: '/shared-robots', icon: Boxes },
    ],
  },
  {
    label: 'AI 工具',
    items: [
      { label: 'AI 诊断工作台', to: '/agent/workbench', icon: Bot },
    ],
  },
]

const ADMIN_NAV: NavGroup[] = [
  { label: '概览', items: [{ label: '系统概览', to: '/admin/console', icon: LayoutDashboard }] },
  ...TEACHER_NAV,
]

export const LAYOUT_CONFIG: Record<UserRole, LayoutConfig> = {
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
