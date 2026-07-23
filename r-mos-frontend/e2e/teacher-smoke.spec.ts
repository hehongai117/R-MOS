// e2e/teacher-smoke.spec.ts
import { test, expect } from '@playwright/test'
import { ACCOUNTS, login } from './helpers'

test('教师登录后教学监控台渲染', async ({ page }) => {
  await login(page, ACCOUNTS.teacher.email, ACCOUNTS.teacher.password)
  await page.waitForURL(/\/(workbench\/teaching|onboarding\/robots)/, { timeout: 15_000 })
  if (page.url().includes('/onboarding')) {
    // 本地教师已 onboard 不会进此分支；CI 新种子可能进——onboarding 页渲染即算通过
    await expect(page.getByText(/机器人|绑定/).first()).toBeVisible({ timeout: 10_000 })
  } else {
    await expect(page.getByText(/班级|监控|学生/).first()).toBeVisible({ timeout: 10_000 })
  }
})

test('SOP 管理页渲染', async ({ page }) => {
  await login(page, ACCOUNTS.teacher.email, ACCOUNTS.teacher.password)
  await page.goto('/sops')
  // SOPListPage 渲染 h2 标题"标准操作流程（SOP）"，或内容区至少含"SOP"文字
  await expect(page.getByText(/SOP/).first()).toBeVisible({ timeout: 10_000 })
})
