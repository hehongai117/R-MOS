import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
    listClassesMock,
    listAssignmentsMock,
    listAssignmentAttemptsMock,
    getStudentProfileMock,
    getWeakStepsMock,
    getTrainingSessionsMock,
} = vi.hoisted(() => ({
    listClassesMock: vi.fn(),
    listAssignmentsMock: vi.fn(),
    listAssignmentAttemptsMock: vi.fn(),
    getStudentProfileMock: vi.fn(),
    getWeakStepsMock: vi.fn(),
    getTrainingSessionsMock: vi.fn(),
}))

vi.mock('@/api/teaching', () => ({
    listClasses: listClassesMock,
    listAssignments: listAssignmentsMock,
    listAssignmentAttempts: listAssignmentAttemptsMock,
}))

vi.mock('@/api/training', () => ({
    getStudentProfile: getStudentProfileMock,
    getWeakSteps: getWeakStepsMock,
    getTrainingSessions: getTrainingSessionsMock,
}))

import TeacherStudentsPage from '@/teaching/pages/TeacherStudentsPage'

describe('TeacherStudentsPage', () => {
    beforeEach(() => {
        listClassesMock.mockReset().mockResolvedValue([
            { id: 1, name: '机器人维保 A 班', term: '2026春' },
        ])
        listAssignmentsMock.mockReset().mockResolvedValue([
            { id: 10, classId: 1, title: '减速器拆装' },
        ])
        listAssignmentAttemptsMock.mockReset().mockResolvedValue([
            { id: 100, assignmentId: 10, studentId: 42, status: 'completed', score: 85, attemptIndex: 1 },
            { id: 101, assignmentId: 10, studentId: 43, status: 'in_progress', score: null, attemptIndex: 1 },
        ])
        getStudentProfileMock.mockReset()
        getWeakStepsMock.mockReset()
        getTrainingSessionsMock.mockReset()
    })

    it('renders page header and loads class students', async () => {
        render(<TeacherStudentsPage />)

        await waitFor(() => {
            expect(screen.getByText('学员档案')).toBeTruthy()
        })

        await waitFor(() => {
            expect(screen.getByText(/学员 #42/)).toBeTruthy()
        })
        expect(screen.getByText(/学员 #43/)).toBeTruthy()
    })

    it('shows student detail when clicked', async () => {
        getStudentProfileMock.mockResolvedValue({
            user_id: 42, overall_level: 2, total_sessions: 5, total_duration: 3600,
            score_safety: 70, score_procedure: 65, score_precision: 80, score_efficiency: 60, score_tools: 55,
            cert_l1_passed: true, cert_l2_passed: false, cert_l3_eligible: false,
        })
        getWeakStepsMock.mockResolvedValue([])
        getTrainingSessionsMock.mockResolvedValue([])

        const user = userEvent.setup()
        render(<TeacherStudentsPage />)

        await waitFor(() => {
            expect(screen.getByText(/学员 #42/)).toBeTruthy()
        })

        await user.click(screen.getByText(/学员 #42/))

        await waitFor(() => {
            expect(screen.getByText('Lv.2')).toBeTruthy()
        })
        expect(getStudentProfileMock).toHaveBeenCalledWith(42)
        expect(getWeakStepsMock).toHaveBeenCalledWith(42)
    })

    it('shows empty state when no students in class', async () => {
        listAssignmentAttemptsMock.mockResolvedValue([])

        render(<TeacherStudentsPage />)

        await waitFor(() => {
            expect(screen.getByText('暂无学员数据')).toBeTruthy()
        })
    })

    it('shows select prompt when no student selected', async () => {
        render(<TeacherStudentsPage />)

        await waitFor(() => {
            expect(screen.getByText('选择学员')).toBeTruthy()
        })
    })
})
