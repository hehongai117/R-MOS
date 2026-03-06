import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DisassemblyDemoAdjudicated } from '@/components/Viewer3D/DisassemblyDemoAdjudicated'

vi.mock('@react-three/fiber', () => ({
  useFrame: () => undefined,
}))

vi.mock('@/adjudication', () => ({
  ActionType: {
    EXTRACT_SCREW: 'extract_screw',
  },
  AdjudicationResult: {
    ALLOWED: 'allowed',
    BLOCKED: 'blocked',
  },
  adjudicateAction: () => ({
    result: 'allowed',
  }),
  validateScrewExtraction: () => ({
    result: 'allowed',
  }),
  commitScrewExtraction: () => undefined,
  useAdjudicationStore: (selector: (state: { currentToolId: string | null }) => unknown) =>
    selector({ currentToolId: 'hex-key' }),
}))

describe('DisassemblyDemoAdjudicated', () => {
  it('renders a screw target group without crashing', () => {
    const { container } = render(
      <DisassemblyDemoAdjudicated
        isPlaying={false}
        screwId="M3x8"
        targetPosition={[0, 0, 0]}
      />,
    )

    expect(container.querySelector('group')).toBeTruthy()
  })
})
