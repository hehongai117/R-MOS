import { describe, expect, it } from 'vitest'

import { BRAND_NAME, APP_VERSION, COPYRIGHT_YEAR, COPYRIGHT_LINE } from '@/config/brand'
import { LAYOUT_CONFIG } from '@/config/nav'
import { ROUTE_PERMISSIONS, getAllowedRoles } from '@/config/routes'

// ─── nav.ts ───────────────────────────────────────────────────────────────────

describe('LAYOUT_CONFIG (nav.ts)', () => {
  const roles = ['student', 'teacher', 'admin'] as const

  it('应包含 student、teacher、admin 三个角色的配置', () => {
    for (const role of roles) {
      expect(LAYOUT_CONFIG[role]).toBeDefined()
    }
  })

  it('每个角色的 LayoutConfig 都有 badgeLabel、badgeVariant、navGroups', () => {
    for (const role of roles) {
      const cfg = LAYOUT_CONFIG[role]
      expect(typeof cfg.badgeLabel).toBe('string')
      expect(['default', 'success', 'destructive']).toContain(cfg.badgeVariant)
      expect(Array.isArray(cfg.navGroups)).toBe(true)
      expect(cfg.navGroups.length).toBeGreaterThan(0)
    }
  })

  it('每个 NavItem 都有 label、to、icon', () => {
    for (const role of roles) {
      const groups = LAYOUT_CONFIG[role].navGroups
      for (const group of groups) {
        expect(typeof group.label).toBe('string')
        expect(Array.isArray(group.items)).toBe(true)
        for (const item of group.items) {
          expect(typeof item.label).toBe('string')
          expect(typeof item.to).toBe('string')
          expect(item.to.startsWith('/')).toBe(true)
          // LucideIcon can be a function or an object (forwardRef component)
          expect(['function', 'object']).toContain(typeof item.icon)
        }
      }
    }
  })

  it('student 配置包含 /dashboard、/my-tasks、/scenarios', () => {
    const studentRoutes = LAYOUT_CONFIG.student.navGroups
      .flatMap(g => g.items)
      .map(i => i.to)
    expect(studentRoutes).toContain('/dashboard')
    expect(studentRoutes).toContain('/my-tasks')
    expect(studentRoutes).toContain('/scenarios')
  })

  it('student 配置不包含仅教师可用的路由 /knowledge、/sops、/teacher/students', () => {
    const studentRoutes = LAYOUT_CONFIG.student.navGroups
      .flatMap(g => g.items)
      .map(i => i.to)
    expect(studentRoutes).not.toContain('/knowledge')
    expect(studentRoutes).not.toContain('/sops')
    expect(studentRoutes).not.toContain('/teacher/students')
  })

  it('teacher 配置包含教学管理路由 /knowledge、/sops、/teacher/students', () => {
    const teacherRoutes = LAYOUT_CONFIG.teacher.navGroups
      .flatMap(g => g.items)
      .map(i => i.to)
    expect(teacherRoutes).toContain('/knowledge')
    expect(teacherRoutes).toContain('/sops')
    expect(teacherRoutes).toContain('/teacher/students')
  })

  it('admin 配置包含 teacher 的所有路由（因为 ADMIN_NAV 展开了 TEACHER_NAV）', () => {
    const teacherRoutes = LAYOUT_CONFIG.teacher.navGroups
      .flatMap(g => g.items)
      .map(i => i.to)
    const adminRoutes = LAYOUT_CONFIG.admin.navGroups
      .flatMap(g => g.items)
      .map(i => i.to)
    for (const route of teacherRoutes) {
      expect(adminRoutes).toContain(route)
    }
  })

  it('admin 额外包含 /admin/console', () => {
    const adminRoutes = LAYOUT_CONFIG.admin.navGroups
      .flatMap(g => g.items)
      .map(i => i.to)
    expect(adminRoutes).toContain('/admin/console')
  })

  it('badge 标签正确：学员/教师/管理员', () => {
    expect(LAYOUT_CONFIG.student.badgeLabel).toBe('学员')
    expect(LAYOUT_CONFIG.teacher.badgeLabel).toBe('教师')
    expect(LAYOUT_CONFIG.admin.badgeLabel).toBe('管理员')
  })
})

// ─── routes.ts ────────────────────────────────────────────────────────────────

describe('ROUTE_PERMISSIONS & getAllowedRoles (routes.ts)', () => {
  it('ROUTE_PERMISSIONS 是一个非空对象', () => {
    expect(typeof ROUTE_PERMISSIONS).toBe('object')
    expect(Object.keys(ROUTE_PERMISSIONS).length).toBeGreaterThan(0)
  })

  it('student-only 路由只允许 student', () => {
    const studentOnlyPaths = ['dashboard', 'my-tasks', 'scenarios', 'student/skills']
    for (const path of studentOnlyPaths) {
      const roles = getAllowedRoles(path)
      expect(roles).toBeDefined()
      expect(roles).toContain('student')
      expect(roles).not.toContain('teacher')
      expect(roles).not.toContain('admin')
    }
  })

  it('teacher/admin 路由包含 teacher 和 admin', () => {
    const teacherAdminPaths = [
      'workbench/teaching',
      'teacher/students',
      'sops',
      'knowledge',
      'shared-robots',
      'teaching/assignments',
    ]
    for (const path of teacherAdminPaths) {
      const roles = getAllowedRoles(path)
      expect(roles).toBeDefined()
      expect(roles).toContain('teacher')
      expect(roles).toContain('admin')
      expect(roles).not.toContain('student')
    }
  })

  it('admin 专属路由只允许 admin', () => {
    const roles = getAllowedRoles('admin/console')
    expect(roles).toBeDefined()
    expect(roles).toContain('admin')
    expect(roles).not.toContain('student')
    expect(roles).not.toContain('teacher')
  })

  it('公开路由 (undefined) 表示任何已认证用户可访问', () => {
    const publicPaths = ['monitor', 'maintenance', 'settings', '3d-viewer', 'agent/workbench', 'reports']
    for (const path of publicPaths) {
      expect(getAllowedRoles(path)).toBeUndefined()
    }
  })

  it('不存在的路由返回 undefined', () => {
    expect(getAllowedRoles('nonexistent/route')).toBeUndefined()
  })
})

// ─── brand.ts ─────────────────────────────────────────────────────────────────

describe('Brand constants (brand.ts)', () => {
  it('BRAND_NAME 为 R-MOS', () => {
    expect(BRAND_NAME).toBe('R-MOS')
  })

  it('APP_VERSION 为 0.2.0', () => {
    expect(APP_VERSION).toBe('0.2.0')
  })

  it('COPYRIGHT_YEAR 为 2026', () => {
    expect(COPYRIGHT_YEAR).toBe('2026')
  })

  it('COPYRIGHT_LINE 包含 BRAND_NAME 和 APP_VERSION', () => {
    expect(COPYRIGHT_LINE).toContain(BRAND_NAME)
    expect(COPYRIGHT_LINE).toContain(APP_VERSION)
    expect(COPYRIGHT_LINE).toContain(COPYRIGHT_YEAR)
  })

  it('COPYRIGHT_LINE 格式正确 (© 年份 品牌 · v版本)', () => {
    expect(COPYRIGHT_LINE).toBe(`© ${COPYRIGHT_YEAR} ${BRAND_NAME} · v${APP_VERSION}`)
  })
})
