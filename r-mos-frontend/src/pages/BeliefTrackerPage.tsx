import { useState } from 'react'
import { PageHeader } from '@/components/common'
import { apiClient } from '@/api/client'

interface BeliefEntry {
    key: string
    value: any
    confidence: number
    source: string
}

interface ConflictEntry {
    field: string
    sources: { source: string; value: any }[]
    resolved: boolean
}

export default function BeliefTrackerPage() {
    const [traceId, setTraceId] = useState('')
    const [beliefs, setBeliefs] = useState<BeliefEntry[]>([])
    const [conflicts, setConflicts] = useState<ConflictEntry[]>([])
    const [worldModel, setWorldModel] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState<'beliefs' | 'conflicts' | 'world'>('beliefs')

    const load = async () => {
        if (!traceId.trim()) return
        setLoading(true)
        try {
            const [bRes, cRes, wRes] = await Promise.allSettled([
                apiClient.get(`/api/v1/agent/belief/${traceId}/beliefs`),
                apiClient.get(`/api/v1/agent/belief/${traceId}/conflicts`),
                apiClient.get(`/api/v1/agent/belief/${traceId}/world-model`),
            ])
            setBeliefs(bRes.status === 'fulfilled' ? (bRes.value.data?.beliefs ?? []) : [])
            setConflicts(cRes.status === 'fulfilled' ? (cRes.value.data?.conflicts ?? []) : [])
            setWorldModel(wRes.status === 'fulfilled' ? (wRes.value.data ?? null) : null)
        } finally {
            setLoading(false)
        }
    }

    const tabs = [
        { key: 'beliefs' as const, label: '信念状态', count: beliefs.length },
        { key: 'conflicts' as const, label: '冲突检测', count: conflicts.length },
        { key: 'world' as const, label: '世界模型', count: worldModel ? 1 : 0 },
    ]

    return (
        <div>
            <PageHeader title="信念追踪" subtitle="查看 Agent 决策过程中的信念状态、冲突和世界模型" />

            <div className="mt-6 flex items-center gap-3">
                <input
                    type="text"
                    value={traceId}
                    onChange={(e) => setTraceId(e.target.value)}
                    placeholder="输入 Trace ID…"
                    className="flex-1 rounded-lg border border-border-subtle bg-bg-surface px-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
                    onKeyDown={(e) => e.key === 'Enter' && void load()}
                />
                <button
                    onClick={() => void load()}
                    disabled={loading || !traceId.trim()}
                    className="rounded-lg bg-primary px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/80 disabled:opacity-50"
                >
                    {loading ? '加载中…' : '查询'}
                </button>
            </div>

            {(beliefs.length > 0 || conflicts.length > 0 || worldModel) && (
                <>
                    <div className="mt-6 flex gap-1 border-b border-border-subtle">
                        {tabs.map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`px-4 py-2.5 text-sm font-medium transition-colors ${activeTab === tab.key
                                        ? 'border-b-2 border-primary text-primary'
                                        : 'text-text-secondary hover:text-text-primary'
                                    }`}
                            >
                                {tab.label}
                                {tab.count > 0 && (
                                    <span className="ml-1.5 rounded-full bg-bg-elevated px-1.5 py-0.5 text-[11px]">{tab.count}</span>
                                )}
                            </button>
                        ))}
                    </div>

                    <div className="mt-4">
                        {activeTab === 'beliefs' && (
                            <div className="overflow-hidden rounded-lg border border-border-subtle">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-border-subtle bg-bg-surface">
                                            <th className="px-4 py-3 text-left font-medium text-text-secondary">键</th>
                                            <th className="px-4 py-3 text-left font-medium text-text-secondary">值</th>
                                            <th className="px-4 py-3 text-center font-medium text-text-secondary">置信度</th>
                                            <th className="px-4 py-3 text-left font-medium text-text-secondary">来源</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border-subtle">
                                        {beliefs.map((b, i) => (
                                            <tr key={i} className="hover:bg-bg-elevated/50">
                                                <td className="px-4 py-3 font-mono text-xs">{b.key}</td>
                                                <td className="px-4 py-3 text-xs">{typeof b.value === 'object' ? JSON.stringify(b.value) : String(b.value)}</td>
                                                <td className="px-4 py-3 text-center">
                                                    <div className="mx-auto w-16 rounded-full bg-bg-elevated">
                                                        <div className="h-1.5 rounded-full bg-primary" style={{ width: `${(b.confidence * 100)}%` }} />
                                                    </div>
                                                    <span className="text-[11px] text-text-muted">{(b.confidence * 100).toFixed(0)}%</span>
                                                </td>
                                                <td className="px-4 py-3 text-xs text-text-secondary">{b.source}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {activeTab === 'conflicts' && (
                            <div className="space-y-3">
                                {conflicts.length === 0 ? (
                                    <p className="text-center text-sm text-text-muted">无冲突</p>
                                ) : (
                                    conflicts.map((c, i) => (
                                        <div key={i} className="rounded-lg border border-border-subtle p-4">
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono text-sm font-medium">{c.field}</span>
                                                <span className={`rounded-full px-2 py-0.5 text-[11px] ${c.resolved ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                                                    }`}>
                                                    {c.resolved ? '已解决' : '未解决'}
                                                </span>
                                            </div>
                                            <div className="mt-2 space-y-1">
                                                {c.sources.map((s, j) => (
                                                    <div key={j} className="flex items-center gap-2 text-xs text-text-secondary">
                                                        <span className="font-medium">{s.source}:</span>
                                                        <span className="font-mono">{typeof s.value === 'object' ? JSON.stringify(s.value) : String(s.value)}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}

                        {activeTab === 'world' && (
                            <div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
                                <pre className="max-h-[500px] overflow-auto whitespace-pre-wrap font-mono text-xs text-text-secondary">
                                    {worldModel ? JSON.stringify(worldModel, null, 2) : '无世界模型数据'}
                                </pre>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}
