import { test, expect, type Page } from '@playwright/test'
import { ACCOUNTS, login, ensureRobotSelected } from './helpers'

const API_BASE = 'http://localhost:8000/api/v1'
const KNEE_SOP_TITLE = 'ATOM-01 左膝关节轴承更换'

type PipelineTask = { task_id: number; execution_id: number }
type AdjudicationSOP = {
  sopId: string
  title: string
  steps: Array<Record<string, unknown> & { action: string }>
}
type AdjudicationSOPList = { total: number; items: AdjudicationSOP[] }

async function resolveKneeSopId(page: Page): Promise<string> {
  const token = await page.evaluate(() => localStorage.getItem('rmos_access_token'))
  expect(token).toBeTruthy()

  const response = await page.request.get(`${API_BASE}/sops/adjudication`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(response.ok()).toBeTruthy()
  const body = await response.json() as AdjudicationSOPList
  expect(Array.isArray(body.items)).toBe(true)

  const knee = body.items.find(
    (sop) => sop.title === KNEE_SOP_TITLE && sop.steps.length === 22,
  )
  expect(knee, '未找到 22 步膝关节 SOP，请先运行 seed_adjudication_sops.py').toBeTruthy()
  return knee!.sopId
}

async function createExecution(page: Page): Promise<PipelineTask> {
  const token = await page.evaluate(() => localStorage.getItem('rmos_access_token'))
  expect(token).toBeTruthy()

  const preference = await page.request.get(`${API_BASE}/agent/preference`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(preference.ok()).toBeTruthy()
  const { user_id: studentId } = await preference.json() as { user_id: number }

  const response = await page.request.post(`${API_BASE}/pipeline/tasks/from-diagnosis`, {
    data: {
      diagnosis_trace_id: `e2e-sop-three-phase-${Date.now()}`,
      fault_type: 'E002_BEARING_WEAR',
      student_id: studentId,
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json() as Promise<PipelineTask>
}

/**
 * Keep the real 22-step SOP, phases and checklist validations, while replacing
 * physical 3D actions with document bridge steps. Canvas coordinates and grouped
 * screw rows are not stable E2E selectors; their adjudication is covered by unit
 * tests. Pipeline requests still go to the real backend and database.
 */
async function makePhysicalStepsDeterministic(page: Page, sopId: string) {
  await page.route('**/api/v1/sops/adjudication**', async (route) => {
    const response = await route.fetch()
    const body = await response.json() as AdjudicationSOPList
    const target = body.items.find((item) => item.sopId === sopId)
    if (target) {
      target.steps = target.steps.map((step) => {
        if (step.action === 'confirm_kit' || step.action === 'verify_check') return step
        return {
          ...step,
          action: 'focus_camera',
          targetParts: [],
          validations: [],
          requiredTool: null,
        }
      })
    }
    await route.fulfill({ response, json: body })
  })
}

async function completeChecklistStep(page: Page) {
  const checklist = page.locator('.ant-card').filter({
    has: page.getByText(/^(齐套检查|验收记录)$/, { exact: true }),
  }).last()
  const unchecked = checklist.locator('.ant-checkbox-input:not(:checked)')
  while (await unchecked.count()) {
    await unchecked.first().check()
  }
  const startButton = page
    .getByRole('button', { name: '下一步' })
    .or(page.getByRole('button', { name: '完成' }))
    .first()
  await expect(startButton).toBeVisible()
  await startButton.click()
  const validateButton = page.getByRole('button', { name: '手动验证' }).first()
  await expect(validateButton).toBeVisible()
  await validateButton.click()
}

async function expectCurrentStep(page: Page, title: string) {
  await expect(page.getByText(title, { exact: true }).first()).toBeVisible({ timeout: 10_000 })
}

test('三段式 SOP：阶段门、齐套门与完成记录', async ({ page }) => {
  await login(page, ACCOUNTS.student.email, ACCOUNTS.student.password)
  await ensureRobotSelected(page)
  const kneeSopId = await resolveKneeSopId(page)
  const { task_id: taskId, execution_id: executionId } = await createExecution(page)
  await makePhysicalStepsDeterministic(page, kneeSopId)

  await page.goto(`/maintenance?sop=${encodeURIComponent(kneeSopId)}&execution_id=${executionId}`)
  await expect(page.getByText('SOP 播放器 (裁决级)')).toBeVisible({ timeout: 20_000 })
  await expectCurrentStep(page, '故障确认')

  await test.step('prep 未完成时 execute 与 verify 保持锁定', async () => {
    await expect(page.getByLabel('执行 阶段未解锁')).toBeVisible()
    await expect(page.getByLabel('验证 阶段未解锁')).toBeVisible()
  })

  // kbr-01 is a deterministic document bridge in this E2E harness.
  await page.getByRole('button', { name: '下一步' }).first().click()
  await expectCurrentStep(page, '断电隔离确认')
  await completeChecklistStep(page)
  await expectCurrentStep(page, '工具齐套')

  await test.step('齐套未勾满时不能推进', async () => {
    const kitCard = page.locator('.ant-card').filter({ hasText: '齐套检查' }).last()
    const kitChecks = kitCard.locator('.ant-checkbox-input')
    expect(await kitChecks.count()).toBeGreaterThan(1)
    await kitChecks.first().check()
    await page.getByRole('button', { name: '下一步' }).first().click()
    await page.getByRole('button', { name: '手动验证' }).first().click()
    await expect(page.getByText('操作被阻断').first()).toBeVisible()
    await expectCurrentStep(page, '工具齐套')

    const blockedDialog = page.getByRole('dialog', { name: /操作被阻断/ })
    await expect(blockedDialog).toBeVisible()
    await blockedDialog.getByRole('button', { name: '我知道了' }).click()
    await expect(blockedDialog).toBeHidden()

    const remaining = kitCard.locator('.ant-checkbox-input:not(:checked)')
    while (await remaining.count()) {
      await remaining.first().check()
    }
    await expect(kitCard.getByText('齐套完成', { exact: true })).toBeVisible()

    const retryButton = page.getByRole('button', { name: '重试' }).first()
    await retryButton.scrollIntoViewIfNeeded()
    await expect(retryButton).toBeVisible()
    await expect(retryButton).toBeEnabled()
    await retryButton.click()
    const validateButton = page.getByRole('button', { name: '手动验证' }).first()
    await expect(validateButton).toBeVisible()

    const evidenceRequest = page.waitForRequest((request) => {
      if (!request.url().endsWith(`/pipeline/executions/${executionId}/steps/complete`)) return false
      const payload = request.postDataJSON() as { evidence_type?: string }
      return payload.evidence_type === 'kit_checklist'
    })
    await validateButton.click()
    const request = await evidenceRequest
    expect(request.postDataJSON()).toMatchObject({
      evidence_type: 'kit_checklist',
      evidence_value: {
        required_items: expect.any(Array),
        confirmed_items: expect.any(Array),
      },
    })
  })

  await test.step('走完 22 步后报告列表出现本次任务记录', async () => {
    await expectCurrentStep(page, '备件齐套')
    await completeChecklistStep(page)

    // kbr-05..kbr-18: physical adjudication is replaced by deterministic
    // document bridges above, preserving all 14 execute-phase boundaries.
    for (let stepIndex = 5; stepIndex <= 18; stepIndex += 1) {
      await expect(page.getByText(`步骤 ${stepIndex}`, { exact: true }).first()).toBeVisible()
      await page.getByRole('button', { name: '下一步' }).first().click()
    }

    for (const title of [
      '外观间隙复核',
      '紧固扭矩复核',
      '通电',
      '±90° 全行程活动度测试',
    ]) {
      await expectCurrentStep(page, title)
      await completeChecklistStep(page)
    }

    await page.waitForURL(/\/reports(?:\?|$)/, { timeout: 20_000 })
    await expect(page.getByRole('heading', { name: '维保报告' })).toBeVisible()
    const taskRow = page.locator('tr').filter({ hasText: `维保任务: E002_BEARING_WEAR` }).first()
    await expect(taskRow).toBeVisible({ timeout: 15_000 })
    await expect(taskRow.getByRole('button', { name: '查看报告' })).toBeVisible()

    // The created task id is retained in the assertion context for easier
    // diagnosis when the real-environment run fails on seeded data.
    expect(taskId).toBeGreaterThan(0)
  })
})
