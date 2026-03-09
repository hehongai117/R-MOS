import type { MaintenanceDraftResponse } from '@/types/maintenance'

const STORAGE_KEY = 'rmos.maintenance.runtime-workspace'

export interface MaintenanceWorkspaceSession {
  projectId: string | null
  projectLabel?: string
  maintenanceGoal: string
  focusArea: string
  draft: MaintenanceDraftResponse | null
}

function isBrowser() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined'
}

export function readMaintenanceWorkspaceSession(): MaintenanceWorkspaceSession | null {
  if (!isBrowser()) {
    return null
  }

  const raw = window.sessionStorage.getItem(STORAGE_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as MaintenanceWorkspaceSession
  } catch {
    window.sessionStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export function writeMaintenanceWorkspaceSession(session: MaintenanceWorkspaceSession) {
  if (!isBrowser()) {
    return
  }

  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

export function clearMaintenanceWorkspaceSession() {
  if (!isBrowser()) {
    return
  }

  window.sessionStorage.removeItem(STORAGE_KEY)
}
