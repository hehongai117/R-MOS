import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import MyTasksPage from '../MyTasksPage'

describe('MyTasksPage', () => {
  it('renders the page title', () => {
    render(
      <MemoryRouter>
        <MyTasksPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('我的任务')).toBeTruthy()
  })

  it('renders tab filters for task status', () => {
    render(
      <MemoryRouter>
        <MyTasksPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('全部')).toBeTruthy()
    expect(screen.getByText('进行中')).toBeTruthy()
    expect(screen.getByText('已完成')).toBeTruthy()
  })
})
