import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import {
  SOPMaintenanceExamOverlay,
  SOPMaintenanceHeader,
  SOPMaintenanceRightRail,
} from '@/components/Maintenance/SOPMaintenanceShell'

describe('SOPMaintenanceShell', () => {
  it('renders exam header metrics and control slots', () => {
    render(
      <SOPMaintenanceHeader
        operationMode="exam"
        examTimeText="09:58"
        currentScore={86}
        totalPartCount={42}
        selectedToolIndicator={<span>工具已选择</span>}
        viewModeControl={<button type="button">视图切换</button>}
        detailToggleControl={<button type="button">细节开关</button>}
        modeSelectControl={<button type="button">模式选择</button>}
      />,
    )

    expect(screen.getByRole('heading', { name: 'SOP 维保系统' })).toBeTruthy()
    expect(screen.getByText('考试模式')).toBeTruthy()
    expect(screen.getByText('倒计时 09:58')).toBeTruthy()
    expect(screen.getByText('得分 86')).toBeTruthy()
    expect(screen.getByText('42 个零件')).toBeTruthy()
    expect(screen.getByRole('button', { name: '视图切换' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '细节开关' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '模式选择' })).toBeTruthy()
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
})
