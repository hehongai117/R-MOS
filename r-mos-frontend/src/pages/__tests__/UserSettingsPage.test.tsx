import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  getMock,
  patchMock,
  postMock,
  putMock,
  useAuthStoreMock,
} = vi.hoisted(() => ({
  getMock: vi.fn(),
  patchMock: vi.fn(),
  postMock: vi.fn(),
  putMock: vi.fn(),
  useAuthStoreMock: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  apiClient: {
    get: getMock,
    patch: patchMock,
    post: postMock,
    put: putMock,
  },
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: useAuthStoreMock,
}))

import UserSettingsPage from '@/pages/UserSettingsPage'

describe('UserSettingsPage', () => {
  beforeEach(() => {
    getMock.mockReset()
    patchMock.mockReset()
    postMock.mockReset()
    putMock.mockReset()
    useAuthStoreMock.mockImplementation((selector: (state: Record<string, unknown>) => unknown) =>
      selector({
        user: {
          email: 'student@rmos.test',
          full_name: 'Student User',
          role: 'student',
        },
      }),
    )
    getMock.mockResolvedValue({
      data: {
        user_id: 1,
        guidance_mode: 'on_demand',
        guidance_mode_display: '按需指导',
        preferences: {
          llm: {
            provider: 'openai',
            model: 'gpt-4.1-mini',
            base_url: 'https://api.openai.com/v1',
            has_api_key: true,
            api_key_masked: 'sk-********7890',
          },
        },
      },
    })
  })

  it('renders llm configuration fields with existing masked api key info', async () => {
    render(<UserSettingsPage />)

    expect(await screen.findByText('大模型配置')).toBeTruthy()
    expect((screen.getByLabelText('Provider') as HTMLInputElement).value).toBe('openai')
    expect((screen.getByLabelText('模型名称') as HTMLInputElement).value).toBe('gpt-4.1-mini')
    expect((screen.getByLabelText('Base URL') as HTMLInputElement).value).toBe('https://api.openai.com/v1')
    expect(screen.getByText('已保存 API Key：sk-********7890')).toBeTruthy()
  })

  it('submits llm configuration updates', async () => {
    putMock.mockResolvedValue({
      data: {
        user_id: 1,
        guidance_mode: 'on_demand',
        guidance_mode_display: '按需指导',
        preferences: {
          llm: {
            provider: 'anthropic',
            model: 'claude-3-7-sonnet-latest',
            base_url: 'https://api.anthropic.com',
            has_api_key: true,
            api_key_masked: 'sk-ant-****9999',
          },
        },
      },
    })

    const user = userEvent.setup()
    render(<UserSettingsPage />)

    await screen.findByText('大模型配置')
    await user.clear(screen.getByLabelText('Provider'))
    await user.type(screen.getByLabelText('Provider'), 'anthropic')
    await user.clear(screen.getByLabelText('模型名称'))
    await user.type(screen.getByLabelText('模型名称'), 'claude-3-7-sonnet-latest')
    await user.clear(screen.getByLabelText('Base URL'))
    await user.type(screen.getByLabelText('Base URL'), 'https://api.anthropic.com')
    await user.type(screen.getByLabelText('API Key'), 'sk-ant-test-9999')
    await user.click(screen.getByRole('button', { name: '保存大模型配置' }))

    await waitFor(() => {
      expect(putMock).toHaveBeenCalledWith('/api/v1/agent/preference/llm', {
        provider: 'anthropic',
        model: 'claude-3-7-sonnet-latest',
        base_url: 'https://api.anthropic.com',
        api_key: 'sk-ant-test-9999',
      })
    })
  })
})
