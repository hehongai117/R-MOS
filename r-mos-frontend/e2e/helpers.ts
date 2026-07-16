// e2e/helpers.ts
import { Page, expect } from '@playwright/test'

export const ACCOUNTS = {
  student: { email: 'student1@rmos.demo', password: 'Student@123' },
  teacher: { email: 'teacher1@rmos.demo', password: 'Teacher@123' },
} as const

export async function login(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.fill('#login-email', email)
  await page.fill('#login-password', password)
  await page.click('button[type="submit"]')
}

/** 学生进入 dashboard 后确保机器人上下文就绪：多台则点第一张卡，单台自动选中。 */
export async function ensureRobotSelected(page: Page) {
  await page.waitForURL('**/dashboard')
  // RobotCards 仅在多台时渲染选择卡；等页面稳定后按需点击
  const firstCard = page.locator('[data-testid="robot-card"]').first()
  if (await firstCard.isVisible({ timeout: 3000 }).catch(() => false)) {
    await firstCard.click()
  }
  // 上下文写入 localStorage('rmos_current_robot_id')
  await expect
    .poll(async () => page.evaluate(() => localStorage.getItem('rmos_current_robot_id')), {
      timeout: 10_000,
    })
    .not.toBeNull()
}
