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

  it('shows student nav with practice center and maintenance flow', () => {
    renderLayoutForRole('student')

    expect(screen.getByRole('link', { name: '我的任务' }).getAttribute('href')).toBe('/my-tasks')
    expect(screen.getByRole('link', { name: '自主练习' }).getAttribute('href')).toBe('/scenarios')
    expect(screen.getByRole('link', { name: '实时监控' }).getAttribute('href')).toBe('/monitor')
    expect(screen.getByRole('link', { name: 'AI 诊断工作台' }).getAttribute('href')).toBe('/agent/workbench')
    expect(screen.getByRole('link', { name: '维保练习' }).getAttribute('href')).toBe('/maintenance')
    expect(screen.getByRole('link', { name: '我的技能' }).getAttribute('href')).toBe('/student/skills')
    expect(screen.getByRole('link', { name: '3D 展示' }).getAttribute('href')).toBe('/3d-viewer')
  })

  it('shows teacher nav with teaching management and tools', () => {
    renderLayoutForRole('teacher')

    expect(screen.getByRole('link', { name: '班级监控台' }).getAttribute('href')).toBe('/workbench/teaching')
    expect(screen.getByRole('link', { name: '作业管理' }).getAttribute('href')).toBe('/teaching/assignments')
    expect(screen.getByRole('link', { name: '学员档案' }).getAttribute('href')).toBe('/teacher/students')
    expect(screen.getByRole('link', { name: 'SOP 管理' }).getAttribute('href')).toBe('/sops')
    expect(screen.getByRole('link', { name: '实时监控' }).getAttribute('href')).toBe('/monitor')
    expect(screen.getByRole('link', { name: '知识库' }).getAttribute('href')).toBe('/knowledge')
  })

  it('shows admin nav with overview and full management access', () => {
    renderLayoutForRole('admin')

    expect(screen.getByRole('link', { name: '系统概览' }).getAttribute('href')).toBe('/admin/console')
    expect(screen.getByRole('link', { name: '班级监控台' }).getAttribute('href')).toBe('/workbench/teaching')
    expect(screen.getByRole('link', { name: '作业管理' }).getAttribute('href')).toBe('/teaching/assignments')
    expect(screen.getByRole('link', { name: 'SOP 管理' }).getAttribute('href')).toBe('/sops')
    expect(screen.getByRole('link', { name: '知识库' }).getAttribute('href')).toBe('/knowledge')
  })
})
