import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DiagnosisPanel } from '@/components/DiagnosisPanel/DiagnosisPanel'

describe('DiagnosisPanel', () => {
  it('renders industrial empty state when no diagnosis data is available', () => {
    render(
      <DiagnosisPanel
        diagnosisResult={null}
        maintenancePlan={null}
        verificationResult={null}
        isLoading={false}
        onConfirmExecution={() => {}}
        onEscalateToTeacher={() => {}}
      />,
    )

    expect(screen.getByText('等待诊断触发')).toBeTruthy()
    expect(screen.getByText('发送"诊断问题"意图后显示')).toBeTruthy()
  })

  it('disables confirm action when supervisor approval is required', () => {
    render(
      <DiagnosisPanel
        diagnosisResult={{
          success: true,
          primary_hypothesis: {
            fault_code: 'E002_STALL',
            fault_name: '电机堵转',
            confidence: 0.92,
            affected_parts: ['waist'],
            possible_causes: ['机械卡滞'],
            evidence: { joint_id: 'waist' },
          },
          alternative_hypotheses: [
            {
              fault_code: 'E001_OVERHEAT',
              fault_name: '电机过热',
              confidence: 0.48,
              affected_parts: ['waist'],
              possible_causes: ['散热不足'],
              evidence: {},
            },
          ],
          requires_supervisor: true,
          reasoning: '电机堵转引发温度升高，需要先排除机械卡滞。',
          recommended_actions: ['检查减速器'],
          error_message: null,
        }}
        maintenancePlan={{
          success: true,
          plan_id: 'plan-001',
          fault_code: 'E002_STALL',
          fault_name: '电机堵转',
          actions: [
            {
              action_id: 'A-1',
              action_type: 'CHECK',
              target_part: 'waist',
              description: '检查机械卡滞',
              estimated_duration_minutes: 10,
              required_tools: ['扭矩扳手'],
              safety_warnings: ['先断电'],
            },
          ],
          total_duration_minutes: 10,
          requires_supervisor: true,
          validation_required: true,
          error_message: null,
        }}
        verificationResult={{
          success: true,
          plan_id: 'plan-001',
          before_state: { fault_count: 1 },
          after_state: { fault_count: 0 },
          delta_summary: { fault_count: '1 -> 0' },
          verdict: '验证通过',
          failed_steps: [],
        }}
        isLoading={false}
        onConfirmExecution={() => {}}
        onEscalateToTeacher={() => {}}
      />,
    )

    expect(screen.getByText('电机堵转')).toBeTruthy()
    expect(screen.getByText('H1 · E002_STALL')).toBeTruthy()
    expect(screen.getByText('H2 · E001_OVERHEAT')).toBeTruthy()
    expect(screen.getByText('joint_id: waist')).toBeTruthy()
    expect(screen.getByText('机械卡滞')).toBeTruthy()
    expect(screen.getByText('92%')).toBeTruthy()
    expect(screen.getByText('验证通过')).toBeTruthy()
    expect(screen.getByText('关键变化')).toBeTruthy()
    expect(screen.getByText('故障数量')).toBeTruthy()
    expect(screen.queryByText('fault_count')).toBeNull()
    expect(screen.getByRole('button', { name: '确认执行方案' }).getAttribute('disabled')).not.toBeNull()
    expect(screen.getByRole('button', { name: '上报教师审核' }).getAttribute('disabled')).toBeNull()
  })

  it('translates simulation highlight keys into business-friendly chinese labels', () => {
    render(
      <DiagnosisPanel
        diagnosisResult={{
          success: true,
          primary_hypothesis: {
            fault_code: 'NORMAL',
            fault_name: '正常',
            confidence: 1,
            affected_parts: [],
            possible_causes: [],
            evidence: {},
          },
          alternative_hypotheses: [],
          requires_supervisor: false,
          reasoning: '未检测到异常。',
          recommended_actions: [],
          error_message: null,
        }}
        maintenancePlan={null}
        verificationResult={{
          success: false,
          plan_id: 'plan-002',
          before_state: {},
          after_state: {},
          delta_summary: {
            'Knee Right.Temperature': '39.47013653444351 -> 40.683005214056934',
          },
          verdict: '验证未通过',
          failed_steps: [],
        }}
        isLoading={false}
        onConfirmExecution={() => {}}
        onEscalateToTeacher={() => {}}
      />,
    )

    expect(screen.getByText('右膝温度')).toBeTruthy()
    expect(screen.getByText('39.47 -> 40.68')).toBeTruthy()
    expect(screen.queryByText('Knee Right.Temperature')).toBeNull()
    expect(screen.queryByText('39.47013653444351 -> 40.683005214056934')).toBeNull()
  })
})
