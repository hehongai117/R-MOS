import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'

import { ProtectedRoute, getStoredDefaultRoute } from '@/components/auth/ProtectedRoute'
import { AUTH_STORAGE_KEYS, useAuthStore } from '@/store/authStore'

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      defaultRoute: null,
      isLoading: false,
      isInitialized: true,
    })
  })

  it('redirects unauthenticated user to login', () => {
    render(
      <MemoryRouter initialEntries={['/admin/faults']}>
        <Routes>
          <Route
            path="/admin/faults"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <div>admin-only-page</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>login-page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('login-page')).toBeTruthy()
  })

  it('redirects student away from teacher page using stored default route', () => {
    localStorage.setItem(AUTH_STORAGE_KEYS.defaultRoute, '/workbench/training')
    useAuthStore.setState({
      user: {
        email: 'student@example.com',
        role: 'student',
      },
      accessToken: 'access',
      refreshToken: 'refresh',
      defaultRoute: '/workbench/training',
      isLoading: false,
      isInitialized: true,
    })

    render(
      <MemoryRouter initialEntries={['/teaching/assignments']}>
        <Routes>
          <Route
            path="/teaching/assignments"
            element={
              <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                <div>teacher-only-page</div>
              </ProtectedRoute>
            }
          />
          <Route path="/workbench/training" element={<div>student-home</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('student-home')).toBeTruthy()
    expect(screen.queryByText('teacher-only-page')).toBeNull()
  })

  it('returns stored default route helper fallback', () => {
    expect(getStoredDefaultRoute()).toBe('/login')
    localStorage.setItem(AUTH_STORAGE_KEYS.defaultRoute, '/admin/console')
    expect(getStoredDefaultRoute()).toBe('/admin/console')
  })
})
