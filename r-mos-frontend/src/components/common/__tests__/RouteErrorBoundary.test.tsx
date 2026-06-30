import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, it, expect, vi } from 'vitest'
import { RouteErrorBoundary } from '../RouteErrorBoundary'

const Boom = () => { throw new Error('boom') }

// Suppress React's console.error noise from intentional error boundary tests
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
})
afterEach(() => {
  vi.restoreAllMocks()
})

it('renders fallback (not a blank screen) when a child throws', () => {
  render(<MemoryRouter><RouteErrorBoundary><Boom /></RouteErrorBoundary></MemoryRouter>)
  expect(screen.getByText(/暂时无法显示|加载失败|出错/)).toBeTruthy()
})
it('renders children normally when no error', () => {
  render(<MemoryRouter><RouteErrorBoundary><div>正常内容</div></RouteErrorBoundary></MemoryRouter>)
  expect(screen.getByText('正常内容')).toBeTruthy()
})
