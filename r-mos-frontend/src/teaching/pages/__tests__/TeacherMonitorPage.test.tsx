import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
    listClassesMock,
    listAssignmentsMock,
    listAssignmentAttemptsMock,
    getAttemptMock,
    getStudentProfileMock,
} = vi.hoisted(() => ({
    listClassesMock: vi.fn(),
    listAssignmentsMock: vi.fn(),
    listAssignmentAttemptsMock: vi.fn(),
    getAttemptMock: vi.fn(),
    getStudentProfileMock: vi.fn(),
}))

vi.mock('@/api/teaching', () => ({
    listClasses: listClassesMock,
    listAssignments: listAssignmentsMock,
    listAssignmentAttempts: listAssignmentAttemptsMock,
    getAttempt: getAttemptMock,
}))

vi.mock('@/api/training', () => ({
    getStudentProfile: getStudentProfileMock,
}))

vi.mock('@/hooks/useWebSocket', () => ({
    useWebSocket: () => ({}),
}))

vi.mock('react-router-dom', () => ({
    useNavigate: () => vi.fn(),
}))

import TeacherMonitorPage from '@/teaching/pages/TeacherMonitorPage'

describe('TeacherMonitorPage', () => {
    beforeEach(() => {
        listClassesMock.mockReset().mockResolvedValue([
            { id: 1, name: '维保 A 班', term: '2026春' },
            { id: 2, name: '维保 B 班', term: '2026春' },
        ])
        listAssignmentsMock.mockReset().mockResolvedValue([
            { id: 10, classId: 1, title: '减速器拆装', status: 'published' },
        ])
        listAssignmentAttemptsMock.mockReset().mockResolvedValue([
            { id: 100, assignmentId: 10, studentId: 42, status: 'completed', score: 88, attemptIndex: 1 },
            { id: 101, assignmentId: 10, studentId: 43, status: 'in_progress', score: null, attemptIndex: 1 },
        ])
        getAttemptMock.mockReset().mockImplementation(async (attemptId: number) => ({
            id: attemptId,
            assignmentId: 10,
            studentId: attemptId === 101 ? 43 : 42,
            taskId: null,
            status: attemptId === 101 ? 'in_progress' : 'completed',
            score: attemptId === 101 ? null : 88,
            attemptIndex: 1,
        }))
        getStudentProfileMock.mockReset().mockResolvedValue({
            level: 2,
            total_sessions: 5,
            total_duration: 3600,
            last_trained_at: '2026-03-08T12:00:00Z',
        })
    })

    it('renders page header and class tabs', async () => {
        render(<TeacherMonitorPage />)

        expect(screen.getByRole('heading', { name: '班级监控台' })).toBeTruthy()

        await waitFor(() => {
            expect(screen.getByText('维保 A 班')).toBeTruthy()
        })
        expect(screen.getByText('维保 B 班')).toBeTruthy()
    })

    it('loads assignment attempts for selected class', async () => {
        render(<TeacherMonitorPage />)

        await waitFor(() => {
            expect(listAssignmentsMock).toHaveBeenCalledWith()
        })

        await waitFor(() => {
            expect(listAssignmentAttemptsMock).toHaveBeenCalledWith(10)
        })
    })

    it('displays attempt status labels', async () => {
        render(<TeacherMonitorPage />)

        await waitFor(() => {
            expect(screen.getByText('已完成')).toBeTruthy()
        })
        expect(screen.getByText('训练中')).toBeTruthy()
    })

    it('shows empty state when no attempts', async () => {
        listAssignmentAttemptsMock.mockResolvedValue([])

        render(<TeacherMonitorPage />)

        await waitFor(() => {
            expect(screen.getByText('暂无尝试数据')).toBeTruthy()
        })
    })

    it('disables evidence and diagnosis actions for attempts without linked task', async () => {
        render(<TeacherMonitorPage />)

        const evidenceButton = (await screen.findByText('查看证据')).closest('button')
        const diagnosisButton = (await screen.findByText('查看诊断')).closest('button')

        expect(evidenceButton?.hasAttribute('disabled')).toBe(true)
        expect(diagnosisButton?.hasAttribute('disabled')).toBe(true)
    })
})
