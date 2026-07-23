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
  // 先断言 toast 出现（sonner error toast 有 data-type="error" 或匹配错误文案）
  const errorToast = page.locator(
    '[data-sonner-toast][data-type="error"], [role="status"]:has-text("失败"), [role="status"]:has-text("错误"), [role="status"]:has-text("密码")',
  )
  await expect(errorToast.first()).toBeVisible({ timeout: 5_000 })
  // toast 可见后再确认 URL 仍停留在 /login
  await expect(page).toHaveURL(/\/login/)
})
