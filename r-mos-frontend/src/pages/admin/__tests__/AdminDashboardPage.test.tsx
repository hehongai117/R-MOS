import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const {
    getAdminUsersMock,
    getMonitorAlertsMock,
    getMonitorHealthMock,
    getMonitorMetricsMock,
    getMonitorMetricsHistoryMock,
    getSystemHealthMock,
    listApprovalsMock,
    getAcceptanceReportsMock,
    getCurrentMetricsMock,
} = vi.hoisted(() => ({
    getAdminUsersMock: vi.fn(),
    getMonitorAlertsMock: vi.fn(),
    getMonitorHealthMock: vi.fn(),
    getMonitorMetricsMock: vi.fn(),
    getMonitorMetricsHistoryMock: vi.fn(),
    getSystemHealthMock: vi.fn(),
    listApprovalsMock: vi.fn(),
    getAcceptanceReportsMock: vi.fn(),
    getCurrentMetricsMock: vi.fn(),
}))

vi.mock('@/api/adminConsole', () => ({
    getAdminUsers: getAdminUsersMock,
    getMonitorAlerts: getMonitorAlertsMock,
    getMonitorHealth: getMonitorHealthMock,
    getMonitorMetrics: getMonitorMetricsMock,
    getMonitorMetricsHistory: getMonitorMetricsHistoryMock,
    getSystemHealth: getSystemHealthMock,
}))

vi.mock('@/api/approvals', () => ({
    listApprovals: listApprovalsMock,
}))

vi.mock('@/api/agent-v2', () => ({
    getAcceptanceReports: getAcceptanceReportsMock,
    getCurrentMetrics: getCurrentMetricsMock,
}))

vi.mock('react-router-dom', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => <a href={to}>{children}</a>,
}))

import AdminDashboardPage from '@/pages/admin/AdminDashboardPage'

describe('AdminDashboardPage', () => {
    beforeEach(() => {
        vi.useFakeTimers({ shouldAdvanceTime: true })
        getAdminUsersMock.mockReset().mockResolvedValue({ total: 25, users: [] })
        listApprovalsMock.mockReset().mockResolvedValue({
            count: 3, items: [
                { id: 1, status: 'pending', reason: 'R2 approval', trace_id: 'tr-1', created_at: '2026-03-01' },
            ]
        })
        getCurrentMetricsMock.mockReset().mockResolvedValue({
            metrics: [
                { metric_id: 'm1', name: 'Safety', actual_value: 95.0, status: 'pass' },
                { metric_id: 'm2', name: 'Quality', actual_value: 72.0, status: 'warning' },
            ]
        })
        getAcceptanceReportsMock.mockReset().mockResolvedValue({ reports: [] })
        getMonitorHealthMock.mockReset().mockResolvedValue({ overall_status: 'healthy', websocket_clients: 2, agent_available: true })
        getMonitorMetricsMock.mockReset().mockResolvedValue({ cpu_percent: 45.0, memory_percent: 62.0, disk_percent: 30.0 })
        getMonitorMetricsHistoryMock.mockReset().mockResolvedValue({ metrics: [] })
        getMonitorAlertsMock.mockReset().mockResolvedValue({ alerts: [] })
        getSystemHealthMock.mockReset().mockResolvedValue({ status: 'ok' })
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('renders page header and data cards', async () => {
        render(<AdminDashboardPage />)

        await waitFor(() => {
            expect(screen.getAllByText('系统概览').length).toBeGreaterThanOrEqual(1)
        })
        expect(screen.getByText('用户总数')).toBeTruthy()
        expect(screen.getAllByText('待处理审批').length).toBeGreaterThanOrEqual(1)
        expect(screen.getByText('指标通过率')).toBeTruthy()
    })

    it('shows error state when APIs fail', async () => {
        getAdminUsersMock.mockRejectedValue(new Error('connection failed'))
        listApprovalsMock.mockRejectedValue(new Error('connection failed'))
        getCurrentMetricsMock.mockRejectedValue(new Error('connection failed'))
        getAcceptanceReportsMock.mockRejectedValue(new Error('connection failed'))
        getMonitorHealthMock.mockRejectedValue(new Error('connection failed'))
        getMonitorMetricsMock.mockRejectedValue(new Error('connection failed'))
        getMonitorMetricsHistoryMock.mockRejectedValue(new Error('connection failed'))
        getMonitorAlertsMock.mockRejectedValue(new Error('connection failed'))
        getSystemHealthMock.mockRejectedValue(new Error('connection failed'))

        render(<AdminDashboardPage />)

        await waitFor(() => {
            expect(screen.getByText('系统概览加载失败')).toBeTruthy()
        })
    })

    it('renders empty approval queue message when no pending', async () => {
        listApprovalsMock.mockResolvedValue({ count: 0, items: [] })
        render(<AdminDashboardPage />)

        await waitFor(() => {
            expect(screen.getByText('审批队列清空')).toBeTruthy()
        })
    })
})
