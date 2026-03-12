import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import {
  SOPMaintenanceExamOverlay,
  SOPMaintenanceHeader,
  SOPMaintenanceLeftRail,
  SOPMaintenanceRightRail,
} from '@/components/Maintenance/SOPMaintenanceShell'

describe('SOPMaintenanceShell', () => {
  it('renders minimal header with only the view mode control slot', () => {
    render(
      <SOPMaintenanceHeader
        viewModeControl={<button type="button">视图切换</button>}
      />,
    )

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '视图切换' })).toBeTruthy()
    expect(screen.queryByText('考试模式')).toBeNull()
    expect(screen.queryByText('倒计时 09:58')).toBeNull()
    expect(screen.queryByText('得分 86')).toBeNull()
    expect(screen.queryByText('42 个零件')).toBeNull()
  })

  it('renders right rail quick locate, diagnosis area, and tab content', () => {
    const onTabChange = vi.fn()

    render(
      <SOPMaintenanceRightRail
        rightPanelTab="tool"
        onRightPanelTabChange={onTabChange}
        quickSelectControl={<button type="button">核心件选择</button>}
        diagnosisContent={<div>诊断卡片</div>}
        partPanel={<div>零件详情内容</div>}
        screwPanel={<div>螺丝信息内容</div>}
      />,
    )

    expect(screen.getByText('核心件快速定位')).toBeTruthy()
    expect(screen.getByText('诊断卡片')).toBeTruthy()
    expect(screen.getByText('螺丝信息内容')).toBeTruthy()

    fireEvent.click(screen.getByRole('tab', { name: '零件' }))

    expect(onTabChange).toHaveBeenCalledWith('part')
  })

  it('renders exam overlay and calls reset action', () => {
    const onReset = vi.fn()

    render(
      <SOPMaintenanceExamOverlay
        reasonCode="SAFETY_BLOCK"
        currentScore={72}
        onReset={onReset}
      />,
    )

    expect(screen.getByRole('heading', { name: '考试结束' })).toBeTruthy()
    expect(screen.getByText('原因码：SAFETY_BLOCK')).toBeTruthy()
    expect(screen.getByText('最终得分：72')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '重置' }))

    expect(onReset).toHaveBeenCalledTimes(1)
  })

  it('renders left rail step navigator and control slots', () => {
    render(
      <SOPMaintenanceLeftRail
        sopTitle="更换肘关节模组"
        difficultyLabel="hard"
        currentStepTitle="拆卸外壳"
        steps={[
          {
            stepId: 'step-1',
            title: '拆卸外壳',
            description: '断电后拆除保护罩',
            onFailureAction: 'block',
            hasCriticalFailureReason: true,
          },
          {
            stepId: 'step-2',
            title: '检查线束',
            description: '确认线束固定状态',
          },
        ]}
        isolationControls={<div>部位子组件区</div>}
        sopListContent={<div>SOP 列表区</div>}
        toolSelectorContent={<div>工具选择区</div>}
        sopPlayerContent={<div>SOP 播放器区</div>}
      />,
    )

    expect(screen.getByText('更换肘关节模组')).toBeTruthy()
    expect(screen.getByText('hard')).toBeTruthy()
    expect(screen.getByText('拆卸外壳')).toBeTruthy()
    expect(screen.getByText('检查线束')).toBeTruthy()
    expect(screen.getByLabelText('阻断步骤')).toBeTruthy()
    expect(screen.getByLabelText('高危步骤')).toBeTruthy()
    expect(screen.getByText('部位子组件区')).toBeTruthy()
    expect(screen.getByText('SOP 列表区')).toBeTruthy()
    expect(screen.getByText('工具选择区')).toBeTruthy()
    expect(screen.getByText('SOP 播放器区')).toBeTruthy()
  })
})
