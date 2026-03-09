import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/common'
import { apiClient } from '@/api/client'

interface FeatureFlag {
    name: string
    enabled: boolean
    rollout_pct: number
    description?: string
}

export default function FeatureFlagPage() {
    const [flags, setFlags] = useState<FeatureFlag[]>([])
    const [loading, setLoading] = useState(true)
    const [toggling, setToggling] = useState<string | null>(null)

    const fetchFlags = async () => {
        try {
            const res = await apiClient.get('/api/v1/agent/features')
            const data = res.data?.flags ?? res.data ?? []
            setFlags(Array.isArray(data) ? data : Object.entries(data).map(([name, v]: [string, any]) => ({
                name,
                enabled: v?.enabled ?? v === true,
                rollout_pct: v?.rollout_pct ?? (v === true ? 100 : 0),
                description: v?.description ?? '',
            })))
        } catch {
            setFlags([])
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { void fetchFlags() }, [])

    const toggle = async (name: string, currentlyEnabled: boolean) => {
        setToggling(name)
        try {
            const action = currentlyEnabled ? 'disable' : 'enable'
            await apiClient.post(`/api/v1/agent/features/${name}/${action}`)
            await fetchFlags()
        } finally {
            setToggling(null)
        }
    }

    const setRollout = async (name: string, pct: number) => {
        setToggling(name)
        try {
            await apiClient.post(`/api/v1/agent/features/${name}/rollout`, { percentage: pct })
            await fetchFlags()
        } finally {
            setToggling(null)
        }
    }

    return (
        <div>
            <PageHeader title="Feature Flag 管理" subtitle="启用/禁用系统功能开关，控制灰度发布百分比" />

            {loading ? (
                <div className="mt-8 text-center text-text-muted">加载中…</div>
            ) : flags.length === 0 ? (
                <div className="mt-8 text-center text-text-muted">暂无可管理的 Feature Flag</div>
            ) : (
                <div className="mt-6 overflow-hidden rounded-lg border border-border-subtle">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border-subtle bg-bg-surface">
                                <th className="px-4 py-3 text-left font-medium text-text-secondary">名称</th>
                                <th className="px-4 py-3 text-left font-medium text-text-secondary">描述</th>
                                <th className="px-4 py-3 text-center font-medium text-text-secondary">状态</th>
                                <th className="px-4 py-3 text-center font-medium text-text-secondary">灰度 %</th>
                                <th className="px-4 py-3 text-center font-medium text-text-secondary">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle">
                            {flags.map((flag) => (
                                <tr key={flag.name} className="hover:bg-bg-elevated/50 transition-colors">
                                    <td className="px-4 py-3 font-mono text-xs">{flag.name}</td>
                                    <td className="px-4 py-3 text-text-secondary text-xs">{flag.description || '—'}</td>
                                    <td className="px-4 py-3 text-center">
                                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${flag.enabled
                                                ? 'bg-emerald-500/10 text-emerald-400'
                                                : 'bg-red-500/10 text-red-400'
                                            }`}>
                                            <span className={`h-1.5 w-1.5 rounded-full ${flag.enabled ? 'bg-emerald-400' : 'bg-red-400'}`} />
                                            {flag.enabled ? '启用' : '禁用'}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-center">
                                        <input
                                            type="number"
                                            min={0}
                                            max={100}
                                            value={flag.rollout_pct}
                                            onChange={(e) => void setRollout(flag.name, Number(e.target.value))}
                                            disabled={toggling === flag.name}
                                            className="w-16 rounded border border-border-subtle bg-bg-base px-2 py-1 text-center text-xs"
                                        />
                                    </td>
                                    <td className="px-4 py-3 text-center">
                                        <button
                                            onClick={() => void toggle(flag.name, flag.enabled)}
                                            disabled={toggling === flag.name}
                                            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${flag.enabled
                                                    ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                                                    : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                                                } disabled:opacity-50`}
                                        >
                                            {toggling === flag.name ? '…' : flag.enabled ? '禁用' : '启用'}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
