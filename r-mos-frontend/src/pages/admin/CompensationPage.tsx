import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/common'
import { apiClient } from '@/api/client'

type PlanStatus = 'draft' | 'approved' | 'executing' | 'completed' | 'failed'

interface CompensationPlan {
    plan_id: string
    description: string
    status: PlanStatus
    created_at: string
    steps?: { action: string; target: string; status: string }[]
}

const STATUS_STYLES: Record<PlanStatus, string> = {
    draft: 'bg-slate-500/10 text-slate-400',
    approved: 'bg-blue-500/10 text-blue-400',
    executing: 'bg-amber-500/10 text-amber-400',
    completed: 'bg-emerald-500/10 text-emerald-400',
    failed: 'bg-red-500/10 text-red-400',
}

const STATUS_LABELS: Record<PlanStatus, string> = {
    draft: '草稿',
    approved: '已批准',
    executing: '执行中',
    completed: '已完成',
    failed: '失败',
}

export default function CompensationPage() {
    const [plans, setPlans] = useState<CompensationPlan[]>([])
    const [loading, setLoading] = useState(true)
    const [selectedPlan, setSelectedPlan] = useState<CompensationPlan | null>(null)
    const [actionLoading, setActionLoading] = useState(false)

    const fetchPlans = async () => {
        try {
            const res = await apiClient.get('/api/v1/agent/compensation/plans')
            setPlans(res.data?.plans ?? res.data ?? [])
        } catch {
            setPlans([])
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { void fetchPlans() }, [])

    const loadDetail = async (planId: string) => {
        try {
            const res = await apiClient.get(`/api/v1/agent/compensation/plan/${planId}`)
            setSelectedPlan(res.data)
        } catch {
            // ignore
        }
    }

    const doAction = async (planId: string, action: 'approve' | 'execute' | 'complete') => {
        setActionLoading(true)
        try {
            await apiClient.post(`/api/v1/agent/compensation/plan/${planId}/${action}`)
            await fetchPlans()
            if (selectedPlan?.plan_id === planId) await loadDetail(planId)
        } finally {
            setActionLoading(false)
        }
    }

    return (
        <div>
            <PageHeader title="补偿方案管理" subtitle="查看、审批、执行系统补偿方案" />

            <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* Plans list */}
                <div className="lg:col-span-2">
                    {loading ? (
                        <div className="text-center text-text-muted">加载中…</div>
                    ) : plans.length === 0 ? (
                        <div className="rounded-lg border border-border-subtle py-12 text-center text-text-muted">
                            暂无补偿方案
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {plans.map((plan) => (
                                <button
                                    key={plan.plan_id}
                                    onClick={() => void loadDetail(plan.plan_id)}
                                    className={`block w-full rounded-lg border p-4 text-left transition-colors ${selectedPlan?.plan_id === plan.plan_id
                                            ? 'border-primary bg-primary-muted'
                                            : 'border-border-subtle hover:bg-bg-elevated'
                                        }`}
                                >
                                    <div className="flex items-center justify-between">
                                        <span className="font-mono text-xs text-text-muted">{plan.plan_id}</span>
                                        <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${STATUS_STYLES[plan.status] ?? STATUS_STYLES.draft}`}>
                                            {STATUS_LABELS[plan.status] ?? plan.status}
                                        </span>
                                    </div>
                                    <p className="mt-1 text-sm">{plan.description || '无描述'}</p>
                                    <p className="mt-1 text-xs text-text-muted">{plan.created_at}</p>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Detail panel */}
                <div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
                    {selectedPlan ? (
                        <>
                            <h3 className="text-sm font-semibold">方案详情</h3>
                            <p className="mt-1 text-xs text-text-secondary">{selectedPlan.description}</p>
                            <div className="mt-3 flex items-center gap-2">
                                <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${STATUS_STYLES[selectedPlan.status] ?? ''}`}>
                                    {STATUS_LABELS[selectedPlan.status] ?? selectedPlan.status}
                                </span>
                            </div>

                            {selectedPlan.steps && selectedPlan.steps.length > 0 && (
                                <div className="mt-4">
                                    <h4 className="text-xs font-medium text-text-muted">执行步骤</h4>
                                    <div className="mt-2 space-y-2">
                                        {selectedPlan.steps.map((step, i) => (
                                            <div key={i} className="rounded border border-border-subtle p-2 text-xs">
                                                <span className="font-medium">{step.action}</span>
                                                <span className="text-text-muted"> → {step.target}</span>
                                                <span className={`ml-2 ${step.status === 'done' ? 'text-emerald-400' : 'text-text-muted'}`}>
                                                    [{step.status}]
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="mt-4 flex gap-2">
                                {selectedPlan.status === 'draft' && (
                                    <button
                                        onClick={() => void doAction(selectedPlan.plan_id, 'approve')}
                                        disabled={actionLoading}
                                        className="rounded bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-500/20 disabled:opacity-50"
                                    >
                                        批准
                                    </button>
                                )}
                                {selectedPlan.status === 'approved' && (
                                    <button
                                        onClick={() => void doAction(selectedPlan.plan_id, 'execute')}
                                        disabled={actionLoading}
                                        className="rounded bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-400 hover:bg-amber-500/20 disabled:opacity-50"
                                    >
                                        执行
                                    </button>
                                )}
                                {selectedPlan.status === 'executing' && (
                                    <button
                                        onClick={() => void doAction(selectedPlan.plan_id, 'complete')}
                                        disabled={actionLoading}
                                        className="rounded bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-50"
                                    >
                                        标记完成
                                    </button>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="py-8 text-center text-sm text-text-muted">← 选择方案查看详情</div>
                    )}
                </div>
            </div>
        </div>
    )
}
