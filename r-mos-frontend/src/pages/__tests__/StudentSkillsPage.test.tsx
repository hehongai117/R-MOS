import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
    getStudentProfileMock,
    getWeakStepsMock,
    getTrainingSessionsMock,
    getActiveTrainingSessionMock,
} = vi.hoisted(() => ({
    getStudentProfileMock: vi.fn(),
    getWeakStepsMock: vi.fn(),
    getTrainingSessionsMock: vi.fn(),
    getActiveTrainingSessionMock: vi.fn(),
}))

vi.mock('@/api/training', () => ({
    getStudentProfile: getStudentProfileMock,
    getWeakSteps: getWeakStepsMock,
    getTrainingSessions: getTrainingSessionsMock,
    getActiveTrainingSession: getActiveTrainingSessionMock,
}))

vi.mock('@/store/authStore', () => ({
    useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
        selector({ user: { user_id: 42 } }),
}))

import StudentSkillsPage from '@/pages/StudentSkillsPage'

describe('StudentSkillsPage', () => {
    beforeEach(() => {
        getStudentProfileMock.mockReset()
        getWeakStepsMock.mockReset()
        getTrainingSessionsMock.mockReset()
        getActiveTrainingSessionMock.mockReset()
    })

    it('renders skill dimensions after loading profile', async () => {
        getStudentProfileMock.mockResolvedValue({
            user_id: 42,
            overall_level: 3,
            total_sessions: 10,
            total_duration: 7200,
            last_trained_at: '2026-03-01T10:00:00Z',
            score_safety: 80,
            score_procedure: 70,
            score_precision: 60,
            score_efficiency: 90,
            score_tools: 50,
            cert_l1_passed: true,
            cert_l2_passed: false,
            cert_l3_eligible: false,
        })
        getWeakStepsMock.mockResolvedValue([
            { step_id: 'align_reducer', fail_count: 3, is_resolved: false },
        ])
        getTrainingSessionsMock.mockResolvedValue([])
        getActiveTrainingSessionMock.mockRejectedValue(new Error('none'))

        render(<StudentSkillsPage />)

        await waitFor(() => {
            expect(screen.getAllByText(/Lv\.3/).length).toBeGreaterThanOrEqual(1)
        })
        expect(screen.getAllByText('安全').length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText('效率').length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText('10').length).toBeGreaterThanOrEqual(1) // total sessions
    })

    it('shows empty state when no profile', async () => {
        getStudentProfileMock.mockRejectedValue(new Error('not found'))
        getWeakStepsMock.mockResolvedValue([])
        getTrainingSessionsMock.mockResolvedValue([])
        getActiveTrainingSessionMock.mockRejectedValue(new Error('none'))

        render(<StudentSkillsPage />)

        await waitFor(() => {
            expect(screen.getByText('技能雷达暂不可用')).toBeTruthy()
        })
    })

    it('renders weak steps heatmap', async () => {
        getStudentProfileMock.mockResolvedValue({
            user_id: 42, overall_level: 1, total_sessions: 1, total_duration: 600,
            score_safety: 50, score_procedure: 50, score_precision: 50, score_efficiency: 50, score_tools: 50,
            cert_l1_passed: false, cert_l2_passed: false, cert_l3_eligible: false,
        })
        getWeakStepsMock.mockResolvedValue([
            { step_id: 'prepare_station', fail_count: 5, is_resolved: false },
            { step_id: 'final_check', fail_count: 2, is_resolved: false },
        ])
        getTrainingSessionsMock.mockResolvedValue([])
        getActiveTrainingSessionMock.mockRejectedValue(new Error('none'))

        render(<StudentSkillsPage />)

        await waitFor(() => {
            expect(screen.getByText('准备工位')).toBeTruthy()
        })
        expect(screen.getByText('最终复核')).toBeTruthy()
    })
})
