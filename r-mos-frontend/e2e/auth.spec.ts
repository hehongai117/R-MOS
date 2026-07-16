// e2e/auth.spec.ts
import { test, expect } from '@playwright/test'
import { ACCOUNTS, login } from './helpers'

test('学生登录成功跳转 dashboard', async ({ page }) => {
  await login(page, ACCOUNTS.student.email, ACCOUNTS.student.password)
  await page.waitForURL('**/dashboard')
  await expect(page).toHaveURL(/\/dashboard/)
})

test('教师登录成功跳转教学监控台', async ({ page }) => {
  await login(page, ACCOUNTS.teacher.email, ACCOUNTS.teacher.password)
  await page.waitForURL(/\/(workbench\/teaching|onboarding\/robots)/)
  // teacher 未完成 onboarding 会去 /onboarding/robots——两者都算登录成功
})

test('错误密码停留登录页并出错误提示', async ({ page }) => {
  await login(page, ACCOUNTS.student.email, 'WrongPass@999')
  await expect(page).toHaveURL(/\/login/)
  // sonner toast 错误提示（登录失败/密码错误类文案），宽松匹配避免绑死文案
  // LoginPage 使用 toast.error() via sonner；选择器匹配 data-sonner-toast 或 [role="status"]
  await expect(page.locator('[data-sonner-toast], [role="status"]').first()).toBeVisible({ timeout: 5000 })
})
