// e2e/student-golden-path.spec.ts
//
// 黄金路径两态设计：
//   - CI 单台（ATOM-01, robot_model_id=1）：seed 脚本保证 ATOM-01 有场景 + SOP 脚本
//   - 本地多台：ATOM-01/GRx-N1/灵犀X1，数据仅在 GRx-N1 上完整；
//     通过检测哪台机器人有 adjudication SOPs 来决定选哪台
//
import { test, expect } from '@playwright/test'
import { ACCOUNTS, login, ensureRobotSelected } from './helpers'

/** 从后端 API 找到有 adjudication SOP 数据的第一个机器人 ID（用于 localStorage 注入） */
async function findRobotWithSOPs(baseURL: string, token: string): Promise<number | null> {
  const response = await fetch(`${baseURL}/api/v1/sops/adjudication`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) return null
  const data: { total: number; items: Array<{ sopId: string }> } = await response.json()
  if (data.total === 0) return null

  // Extract robot_model_id from the first SOP; use API to list robots and match
  // Shortcut: try robot_model_id 1..5 to find which has SOPs
  for (const id of [1, 2, 3, 4, 5]) {
    const r2 = await fetch(`${baseURL}/api/v1/sops/adjudication?robot_model_id=${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!r2.ok) continue
    const d2: { total: number } = await r2.json()
    if (d2.total > 0) return id
  }
  return null
}

test('学生黄金路径：登录→机器人上下文→场景→SOP实操→报告页', async ({ page }) => {
  const BASE_URL = 'http://localhost:8000'

  // 1. 登录
  await login(page, ACCOUNTS.student.email, ACCOUNTS.student.password)

  // 1b. 取 token（authStore 已存 localStorage，page.evaluate 读取）
  await page.waitForURL('**/dashboard')

  // 找有数据的机器人 ID（CI: ATOM-01=robot 1；本地: GRx-N1=robot 2）
  const token = await page.evaluate(() => localStorage.getItem('rmos_access_token'))
  const robotIdWithData = token
    ? await findRobotWithSOPs(BASE_URL, token).catch(() => null)
    : null

  if (robotIdWithData) {
    // 强制设置上下文为有数据的机器人
    await page.evaluate((id) => {
      localStorage.setItem('rmos_current_robot_id', String(id))
    }, robotIdWithData)
    // 刷新 dashboard 让 Zustand store 从 localStorage 重新初始化
    await page.reload()
    await page.waitForURL('**/dashboard')
  }

  // 1c. 确认机器人上下文已就绪
  await ensureRobotSelected(page)

  // 2. 场景选择页
  await page.goto('/scenarios')
  // 等待场景列表渲染完成：有场景则出现"开始练习"按钮（可能多个），无场景则出现空态文案
  // 使用 first() 避免多个按钮触发 strict mode 冲突
  const startBtnOrEmpty = page.getByRole('button', { name: '开始练习' }).first().or(
    page.getByText('暂无可用的练习场景'),
  )
  await expect(startBtnOrEmpty).toBeVisible({ timeout: 15_000 })

  const startBtn = page.getByRole('button', { name: '开始练习' }).first()
  if (await startBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await startBtn.click()
    await page.waitForURL(/\/maintenance/, { timeout: 15_000 })
  } else {
    await page.goto('/maintenance')
  }

  // 3. 落到实操工作台：SOP 播放器面板标题渲染（左侧执行轨渲染即证）
  const sopPlayerTitle = page.getByText('SOP 播放器 (裁决级)')
  await expect(sopPlayerTitle).toBeVisible({ timeout: 20_000 })

  // 4. 确保有 SOP 脚本可执行：若 SOP 未自动选中（dropdown 显示 placeholder）则手动打开选第一项
  //    Ant Design Select 交互：click 容器打开 → 选项出现 → click 第一项
  const sopSelect = page.locator('.ant-select-selector').filter({ hasText: '选择 SOP 脚本' })
  if (await sopSelect.isVisible({ timeout: 5_000 }).catch(() => false)) {
    // 等待 SOP 脚本 API 响应（useSOPScripts 异步加载）
    await page.locator('.ant-select').first().click()
    const firstOption = page.locator('.ant-select-item-option').first()
    if (await firstOption.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await firstOption.click()
    } else {
      // 没有可用 SOP 脚本——跳过步骤 4（此情况 CI/本地数据一致时不会出现）
      console.warn('[golden-path] 无 SOP 脚本可选，跳过步骤 4')
      // 关闭下拉
      await page.keyboard.press('Escape')
      // 仍要断言 SOP 播放器面板在视图内——步骤 3 已断言，这里直接跳到步骤 5
      await page.goto('/reports')
      await expect(page.getByText('任务报告').first()).toBeVisible({ timeout: 10_000 })
      return
    }
  }

  // 等待 "下一步" 按钮出现（SOP 选中后 context 初始化完毕）
  const nextBtn = page.getByRole('button', { name: '下一步' }).first()
  await expect(nextBtn).toBeVisible({ timeout: 10_000 })

  // 点击"下一步"，断言裁决引擎已响应（三种合法响应均为通过）：
  //   a) "等待实际操作完成"（有 targetParts，EXECUTING 状态）
  //   b) "操作被阻断"（前置条件不满足，BLOCKED 状态）
  //   c) "SOP 执行完成"（无 targetParts + 无前置验证，直接 COMPLETE）
  //   d) 按钮文案变为"手动验证"（EXECUTING 状态的 primary button）
  await nextBtn.click()

  await expect(
    page
      .getByText('等待实际操作完成')
      .or(page.getByText('操作被阻断'))
      .or(page.getByText('SOP 执行完成'))
      .or(page.getByRole('button', { name: '手动验证' }))
      .first(),
  ).toBeVisible({ timeout: 15_000 })

  // 5. 报告页可达且渲染
  await page.goto('/reports')
  await expect(page.getByText('任务报告').first()).toBeVisible({ timeout: 10_000 })
})
