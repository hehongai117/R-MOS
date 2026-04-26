import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import ScenarioPickerPage from '../ScenarioPickerPage'

describe('ScenarioPickerPage', () => {
  it('renders the page title', () => {
    render(
      <MemoryRouter>
        <ScenarioPickerPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('自主练习')).toBeTruthy()
  })

  it('renders difficulty filter options', () => {
    render(
      <MemoryRouter>
        <ScenarioPickerPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('全部')).toBeTruthy()
    expect(screen.getByText('入门')).toBeTruthy()
    expect(screen.getByText('进阶')).toBeTruthy()
    expect(screen.getByText('高级')).toBeTruthy()
  })
})
