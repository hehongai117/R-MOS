import { render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'

import { PartInspector } from '@/components/Viewer3D/PartInspector'

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children?: React.ReactNode }) => <div data-testid="part-inspector-canvas">{children}</div>,
}))

vi.mock('@react-three/drei', () => ({
  Center: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  OrbitControls: () => <div data-testid="orbit-controls" />,
  useGLTF: () => ({
    scene: {
      clone: () => ({
        traverse: () => undefined,
      }),
    },
  }),
}))

describe('PartInspector', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it('shows empty hint when no link is selected', () => {
    render(<PartInspector selectedLink={null} />)

    expect(screen.getByText('点击零件查看详情')).toBeTruthy()
  })

  it('lists torso detail parts when a core link is selected', () => {
    render(<PartInspector selectedLink="torso_link" />)

    expect(screen.getByTestId('part-inspector-canvas')).toBeTruthy()
    expect(screen.getAllByText('躯干主体框架').length).toBeGreaterThan(0)
    expect(screen.getByText('躯干前盖板')).toBeTruthy()
  })
})
