import type { ReactNode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { AUTH_STORAGE_KEYS, useAuthStore } from '@/store/authStore'

vi.mock('@/components/auth/AuthContext', () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('@/components/Layout/AppLayout', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    default: () => (
      <div data-testid="app-layout">
        <actual.Outlet />
      </div>
    ),
  }
})

vi.mock('@/pages/SOPMaintenancePage', () => ({
  default: () => <div>SOPMaintenancePageStub</div>,
}))

describe('App routes', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    localStorage.clear()
    localStorage.setItem(AUTH_STORAGE_KEYS.accessToken, 'access')
    localStorage.setItem(AUTH_STORAGE_KEYS.refreshToken, 'refresh')
    localStorage.setItem(AUTH_STORAGE_KEYS.role, 'student')
    localStorage.setItem(AUTH_STORAGE_KEYS.defaultRoute, '/maintenance')
    localStorage.setItem(AUTH_STORAGE_KEYS.email, 'student@example.com')
    useAuthStore.setState({
      user: {
        email: 'student@example.com',
        full_name: 'student user',
        role: 'student',
      },
      accessToken: 'access',
      refreshToken: 'refresh',
      defaultRoute: '/maintenance',
      isLoading: false,
      isInitialized: true,
    })
  })

  it('redirects the legacy atom01 maintenance route to the sop workbench', async () => {
    window.history.replaceState({}, '', '/workbench/atom01-maintenance')

    render(<App />)

    await waitFor(() => {
      expect(window.location.pathname).toBe('/maintenance')
    })
    expect(screen.getByText('SOPMaintenancePageStub')).toBeTruthy()
  })
})
