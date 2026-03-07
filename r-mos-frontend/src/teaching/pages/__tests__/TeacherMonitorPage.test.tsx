import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
    listClassesMock,
    listAssignmentsMock,
    listAssignmentAttemptsMock,
} = vi.hoisted(() => ({
    listClassesMock: vi.fn(),
    listAssignmentsMock: vi.fn(),
    listAssignmentAttemptsMock: vi.fn(),
}))

vi.mock('@/api/teaching', () => ({
    listClasses: listClassesMock,
    listAssignments: listAssignmentsMock,
    listAssignmentAttempts: listAssignmentAttemptsMock,
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
    })

    it('renders page header and class tabs', async () => {
        render(<TeacherMonitorPage />)

        expect(screen.getByText('班级监控台')).toBeTruthy()

        await waitFor(() => {
            expect(screen.getByText('维保 A 班')).toBeTruthy()
        })
        expect(screen.getByText('维保 B 班')).toBeTruthy()
    })

    it('loads assignment attempts for selected class', async () => {
        render(<TeacherMonitorPage />)

        await waitFor(() => {
            expect(listAssignmentsMock).toHaveBeenCalledWith(1)
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
        expect(screen.getByText('进行中')).toBeTruthy()
    })

    it('shows empty state when no attempts', async () => {
        listAssignmentAttemptsMock.mockResolvedValue([])

        render(<TeacherMonitorPage />)

        await waitFor(() => {
            expect(screen.getByText('暂无提交记录')).toBeTruthy()
        })
    })
})
