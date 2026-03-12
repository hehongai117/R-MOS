import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import ScrewInfo from '@/components/Maintenance/ScrewInfo'
import ToolSelector from '@/components/Maintenance/ToolSelector'

describe('ToolingPanels', () => {
  it('renders tool options as buttons and allows clearing the selected tool', async () => {
    const onToolSelect = vi.fn()
    const user = userEvent.setup()

    render(
      <ToolSelector
        selectedToolId="hex_2.5"
        onToolSelect={onToolSelect}
        requiredScrewId="M3x8"
      />,
    )

    await user.click(screen.getByRole('button', { name: /2\.5mm 内六角扳手/i }))
    expect(onToolSelect).toHaveBeenCalledWith(null)

    await user.click(screen.getByRole('button', { name: '放下工具' }))
    expect(onToolSelect).toHaveBeenLastCalledWith(null)
  })

  it('renders screw entries as buttons and forwards screw selection', async () => {
    const onScrewSelect = vi.fn()
    const user = userEvent.setup()

    render(
      <ScrewInfo
        partName="torso_link"
        onScrewSelect={onScrewSelect}
        selectedScrewId={null}
      />,
    )

    await user.click(screen.getByRole('button', { name: /M4×12/i }))

    expect(onScrewSelect).toHaveBeenCalledWith('M4x12')
  })
})
