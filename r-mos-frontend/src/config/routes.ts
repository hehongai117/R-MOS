import type { UserRole } from '@/store/authStore'

/**
 * Route permission configuration.
 * Maps each route path to the allowed roles.
 * `undefined` means any authenticated user can access the route.
 */
export const ROUTE_PERMISSIONS: Record<string, UserRole[] | undefined> = {
  dashboard: ['student'],
  'my-tasks': ['student'],
  scenarios: ['student'],
  'student/skills': ['student'],
  'workbench/teaching': ['teacher', 'admin'],
  'teacher/students': ['teacher', 'admin'],
  'admin/console': ['admin'],
  sops: ['teacher', 'admin'],
  knowledge: ['teacher', 'admin'],
  'shared-robots': ['teacher', 'admin'],
  monitor: undefined,
  maintenance: undefined,
  '3d-viewer': undefined,
  'teaching/assignments': ['teacher', 'admin'],
  'teaching/attempts/:id': ['teacher', 'admin'],
  'teaching/attempts/:id/evidence': ['teacher', 'admin'],
  'teaching/attempts/:id/diagnosis': ['teacher', 'admin'],
  'agent/workbench': undefined,
  settings: undefined,
  reports: undefined,
  'reports/:taskId': undefined,
}

/**
 * Returns the allowed roles for a given route path.
 * Returns `undefined` if the route is accessible by any authenticated user.
 */
export function getAllowedRoles(path: string): UserRole[] | undefined {
  return ROUTE_PERMISSIONS[path]
}
