import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'

import AppLayout from '@/components/Layout/AppLayout'
import { useAuthStore, type UserRole } from '@/store/authStore'

function renderLayoutForRole(role: UserRole) {
  useAuthStore.setState({
    user: {
      email: `${role}@example.com`,
      full_name: `${role} user`,
      role,
    },
    accessToken: 'access',
    refreshToken: 'refresh',
    defaultRoute: '/',
    isLoading: false,
    isInitialized: true,
  })

  render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<div>home</div>} />
        </Route>
        <Route path="/login" element={<div>login</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AppLayout', () => {
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

  it('shows restored legacy feature links for student users', () => {
    renderLayoutForRole('student')

    expect(screen.getByRole('link', { name: '训练工作台' }).getAttribute('href')).toBe('/workbench/training')
    expect(screen.getByRole('link', { name: 'AI 工作台' }).getAttribute('href')).toBe('/agent/workbench')
    expect(screen.getByRole('link', { name: 'ATOM01 维保工作台' }).getAttribute('href')).toBe('/workbench/atom01-maintenance')
    expect(screen.getByRole('link', { name: 'SOP 工作台' }).getAttribute('href')).toBe('/maintenance')
    expect(screen.getByRole('link', { name: '3D 展示' }).getAttribute('href')).toBe('/atom01')
    expect(screen.getByRole('link', { name: '执行回放' }).getAttribute('href')).toBe('/agent/replay')
  })

  it('keeps teacher workbench links and moves sop tools into workbench', () => {
    renderLayoutForRole('teacher')

    expect(screen.getByRole('link', { name: '班级监控台' }).getAttribute('href')).toBe('/workbench/teaching')
    expect(screen.getByRole('link', { name: 'ATOM01 维保工作台' }).getAttribute('href')).toBe('/workbench/atom01-maintenance')
    expect(screen.getByRole('link', { name: '作业管理' }).getAttribute('href')).toBe('/teaching/assignments')
    expect(screen.getByRole('link', { name: 'SOP 工作台' }).getAttribute('href')).toBe('/maintenance')
    expect(screen.getByRole('link', { name: '实时监控' }).getAttribute('href')).toBe('/monitor')
  })

  it('keeps admin console links and exposes the moved workbench entries', () => {
    renderLayoutForRole('admin')

    expect(screen.getByRole('link', { name: '系统概览' }).getAttribute('href')).toBe('/admin/console')
    expect(screen.getByRole('link', { name: 'ATOM01 维保工作台' }).getAttribute('href')).toBe('/workbench/atom01-maintenance')
    expect(screen.getByRole('link', { name: 'SOP 工作台' }).getAttribute('href')).toBe('/maintenance')
    expect(screen.getByRole('link', { name: '审批队列' }).getAttribute('href')).toBe('/admin/approvals')
    expect(screen.getByRole('link', { name: '知识库' }).getAttribute('href')).toBe('/knowledge')
  })
})
