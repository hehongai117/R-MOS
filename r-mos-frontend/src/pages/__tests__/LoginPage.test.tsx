import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { loginMock, useAuthStoreMock } = vi.hoisted(() => ({
    loginMock: vi.fn(),
    useAuthStoreMock: vi.fn(),
}))

vi.mock('react-router-dom', () => ({
    useNavigate: () => vi.fn(),
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => <a href={to}>{children}</a>,
}))

vi.mock('@/store/authStore', () => ({
    useAuthStore: useAuthStoreMock,
}))

vi.mock('sonner', () => ({
    toast: { error: vi.fn() },
}))

import LoginPage from '@/pages/LoginPage'

describe('LoginPage', () => {
    beforeEach(() => {
        loginMock.mockReset()
        useAuthStoreMock.mockImplementation((selector: (s: Record<string, unknown>) => unknown) =>
            selector({
                defaultRoute: null,
                isInitialized: true,
                isLoading: false,
                login: loginMock,
                user: null,
            })
        )
    })

    it('renders branding and form elements', () => {
        render(<LoginPage />)
        expect(screen.getAllByText('R-MOS').length).toBeGreaterThanOrEqual(1)
        expect(screen.getByPlaceholderText('user@rmos.io')).toBeTruthy()
        expect(screen.getByPlaceholderText('••••••••')).toBeTruthy()
        expect(screen.getByRole('button', { name: '登录' })).toBeTruthy()
    })

    it('renders feature items', () => {
        render(<LoginPage />)
        expect(screen.getByText('SOP 标准操作')).toBeTruthy()
        expect(screen.getByText('AI Agent 决策')).toBeTruthy()
        expect(screen.getByText('技能成长体系')).toBeTruthy()
    })

    it('submits email and password via login', async () => {
        loginMock.mockResolvedValue('/admin/console')
        const user = userEvent.setup()

        render(<LoginPage />)

        await user.type(screen.getByPlaceholderText('user@rmos.io'), 'test@rmos.io')
        await user.type(screen.getByPlaceholderText('••••••••'), 'pass123')
        await user.click(screen.getByRole('button', { name: '登录' }))

        await waitFor(() => {
            expect(loginMock).toHaveBeenCalledWith({
                email: 'test@rmos.io',
                password: 'pass123',
            })
        })
    })

    it('disables button when loading', () => {
        useAuthStoreMock.mockImplementation((selector: (s: Record<string, unknown>) => unknown) =>
            selector({
                defaultRoute: null,
                isInitialized: true,
                isLoading: true,
                login: loginMock,
                user: null,
            })
        )

        render(<LoginPage />)
        const button = screen.getByRole('button')
        expect(button.hasAttribute('disabled')).toBe(true)
        expect(screen.getByText('登录中...')).toBeTruthy()
    })
})
