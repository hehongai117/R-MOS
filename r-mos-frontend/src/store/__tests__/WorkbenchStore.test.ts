import { describe, expect, it } from 'vitest'

import {
  canSubmitCurrentStep,
  createWorkbenchStore,
  getConfirmedCriticalToolCount,
} from '@/store/workbenchStore'

describe('WorkbenchStore', () => {
  it('updates current step via setCurrentStep', () => {
    const store = createWorkbenchStore()

    store.getState().setCurrentStep('step-2')
    expect(store.getState().currentStepId).toBe('step-2')
  })

  it('hydrates a training project and keeps compatibility methods', () => {
    const store = createWorkbenchStore()

    store.getState().hydrateTrainingProject({
      project: {
        sessionId: 'sess-1',
        projectId: 'proj-1',
        title: '减速器拆装训练',
        progressPercent: 50,
      },
      currentStepId: 'step-2',
      steps: [
        {
          id: 'step-1',
          stepIndex: 0,
          title: '准备工装',
          status: 'passed',
          instruction: '检查工具和安全防护。',
          tools: [{ id: 'tool-a', name: '扭矩扳手', isCritical: true }],
        },
        {
          id: 'step-2',
          stepIndex: 1,
          title: '拆解电机盖',
          status: 'active',
          instruction: '按顺序松开固定螺钉。',
          tools: [
            { id: 'tool-b', name: '六角扳手', isCritical: true },
            { id: 'tool-c', name: '记号笔', isCritical: false },
          ],
        },
      ],
    })

    expect(store.getState().project?.title).toBe('减速器拆装训练')
    expect(store.getState().currentStepId).toBe('step-2')
    expect(store.getState().toolStatusMap['tool-a']).toBe('PENDING')
    expect(store.getState().toolStatusMap['tool-b']).toBe('PENDING')

    store.getState().setToolStatus('tool-b', 'CONFIRMED')
    store.getState().setVerdict({ result: 'PASS', summary: '执行准确' })
    expect(store.getState().verdict?.result).toBe('PASS')

    const counter = getConfirmedCriticalToolCount(store.getState())
    expect(counter.confirmed).toBe(1)
    expect(counter.total).toBe(1)
    expect(canSubmitCurrentStep(store.getState())).toBe(true)
  })

  it('updates tool status and resets verdict', () => {
    const store = createWorkbenchStore()

    store.getState().setToolStatus('tool-a', 'CONFIRMED')
    expect(store.getState().toolStatusMap['tool-a']).toBe('CONFIRMED')

    store.getState().setVerdict({ result: 'PASS', summary: 'ok' })
    expect(store.getState().verdict?.result).toBe('PASS')

    store.getState().resetVerdict()
    expect(store.getState().verdict).toBeNull()
  })
})
