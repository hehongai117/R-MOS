import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/common'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/api/client'

export default function UserSettingsPage() {
    const user = useAuthStore((state) => state.user)
    const [fullName, setFullName] = useState(user?.full_name ?? '')
    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [provider, setProvider] = useState('openai')
    const [model, setModel] = useState('')
    const [baseUrl, setBaseUrl] = useState('')
    const [apiKey, setApiKey] = useState('')
    const [maskedApiKey, setMaskedApiKey] = useState<string | null>(null)
    const [saving, setSaving] = useState(false)
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

    useEffect(() => {
        let cancelled = false

        const loadPreference = async () => {
            try {
                const response = await apiClient.get('/api/v1/agent/preference')
                if (cancelled) {
                    return
                }

                const llm = response.data?.preferences?.llm ?? {}
                setProvider(typeof llm.provider === 'string' && llm.provider ? llm.provider : 'openai')
                setModel(typeof llm.model === 'string' ? llm.model : '')
                setBaseUrl(typeof llm.base_url === 'string' ? llm.base_url : '')
                setMaskedApiKey(typeof llm.api_key_masked === 'string' ? llm.api_key_masked : null)
            } catch {
                if (!cancelled) {
                    setMaskedApiKey(null)
                }
            }
        }

        void loadPreference()

        return () => {
            cancelled = true
        }
    }, [])

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault()
        setSaving(true)
        setMessage(null)
        try {
            await apiClient.patch('/api/v1/auth/profile', { full_name: fullName })
            setMessage({ type: 'success', text: '个人信息已更新' })
        } catch {
            setMessage({ type: 'error', text: '更新失败，请重试' })
        } finally {
            setSaving(false)
        }
    }

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault()
        if (newPassword !== confirmPassword) {
            setMessage({ type: 'error', text: '两次输入的密码不一致' })
            return
        }
        if (newPassword.length < 6) {
            setMessage({ type: 'error', text: '密码长度至少 6 位' })
            return
        }
        setSaving(true)
        setMessage(null)
        try {
            await apiClient.post('/api/v1/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword,
            })
            setMessage({ type: 'success', text: '密码已修改' })
            setCurrentPassword('')
            setNewPassword('')
            setConfirmPassword('')
        } catch {
            setMessage({ type: 'error', text: '密码修改失败，请检查当前密码' })
        } finally {
            setSaving(false)
        }
    }

    const handleUpdateLLM = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!provider.trim() || !model.trim() || !baseUrl.trim()) {
            setMessage({ type: 'error', text: '请完整填写 Provider、模型名称和 Base URL' })
            return
        }

        setSaving(true)
        setMessage(null)
        try {
            const response = await apiClient.put('/api/v1/agent/preference/llm', {
                provider: provider.trim(),
                model: model.trim(),
                base_url: baseUrl.trim(),
                api_key: apiKey.trim(),
            })
            const llm = response.data?.preferences?.llm ?? {}
            setMaskedApiKey(typeof llm.api_key_masked === 'string' ? llm.api_key_masked : null)
            setApiKey('')
            setMessage({ type: 'success', text: '大模型配置已保存' })
        } catch {
            setMessage({ type: 'error', text: '大模型配置保存失败，请重试' })
        } finally {
            setSaving(false)
        }
    }

    const inputCls = 'w-full rounded-lg border border-border-subtle bg-bg-surface px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none'
    const labelCls = 'block text-sm font-medium text-text-secondary mb-1.5'
    const btnCls = 'rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary/80 disabled:opacity-50'

    return (
        <div>
            <PageHeader title="个人设置" subtitle="管理账号信息和安全设置" />

            {message && (
                <div className={`mt-4 rounded-lg px-4 py-3 text-sm ${message.type === 'success'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    }`}>
                    {message.text}
                </div>
            )}

            <div className="mt-6 grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
                {/* Profile section */}
                <div className="rounded-lg border border-border-subtle p-6">
                    <h3 className="text-sm font-semibold text-text-primary">基本信息</h3>
                    <form onSubmit={(e) => void handleUpdateProfile(e)} className="mt-4 space-y-4">
                        <div>
                            <label htmlFor="settings-email" className={labelCls}>邮箱</label>
                            <input id="settings-email" type="email" value={user?.email ?? ''} disabled className={`${inputCls} opacity-60`} />
                        </div>
                        <div>
                            <label htmlFor="settings-role" className={labelCls}>角色</label>
                            <input id="settings-role" type="text" value={user?.role ?? ''} disabled className={`${inputCls} opacity-60`} />
                        </div>
                        <div>
                            <label htmlFor="settings-full-name" className={labelCls}>姓名</label>
                            <input id="settings-full-name" type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputCls} placeholder="输入姓名" />
                        </div>
                        <button type="submit" disabled={saving} className={btnCls}>
                            {saving ? '保存中…' : '保存'}
                        </button>
                    </form>
                </div>

                {/* LLM section */}
                <div className="rounded-lg border border-border-subtle p-6">
                    <h3 className="text-sm font-semibold text-text-primary">大模型配置</h3>
                    <p className="mt-2 text-sm text-text-secondary">
                        为当前账号配置专属 Provider、模型和 API Key。配置保存在后端账号偏好中。
                    </p>
                    <form onSubmit={(e) => void handleUpdateLLM(e)} className="mt-4 space-y-4">
                        <div>
                            <label htmlFor="settings-llm-provider" className={labelCls}>Provider</label>
                            <input
                                id="settings-llm-provider"
                                type="text"
                                value={provider}
                                onChange={(e) => setProvider(e.target.value)}
                                className={inputCls}
                                placeholder="openai / anthropic / openrouter"
                            />
                        </div>
                        <div>
                            <label htmlFor="settings-llm-model" className={labelCls}>模型名称</label>
                            <input
                                id="settings-llm-model"
                                type="text"
                                value={model}
                                onChange={(e) => setModel(e.target.value)}
                                className={inputCls}
                                placeholder="例如 gpt-4.1-mini"
                            />
                        </div>
                        <div>
                            <label htmlFor="settings-llm-base-url" className={labelCls}>Base URL</label>
                            <input
                                id="settings-llm-base-url"
                                type="text"
                                value={baseUrl}
                                onChange={(e) => setBaseUrl(e.target.value)}
                                className={inputCls}
                                placeholder="https://api.openai.com/v1"
                            />
                        </div>
                        <div>
                            <label htmlFor="settings-llm-api-key" className={labelCls}>API Key</label>
                            <input
                                id="settings-llm-api-key"
                                type="password"
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                className={inputCls}
                                placeholder="输入新的 API Key，不填则保留当前值"
                            />
                            {maskedApiKey ? (
                                <p className="mt-2 text-xs text-text-muted">已保存 API Key：{maskedApiKey}</p>
                            ) : (
                                <p className="mt-2 text-xs text-text-muted">当前尚未保存 API Key</p>
                            )}
                        </div>
                        <button type="submit" disabled={saving} className={btnCls}>
                            {saving ? '保存中…' : '保存大模型配置'}
                        </button>
                    </form>
                </div>

                {/* Password section */}
                <div className="rounded-lg border border-border-subtle p-6">
                    <h3 className="text-sm font-semibold text-text-primary">修改密码</h3>
                    <form onSubmit={(e) => void handleChangePassword(e)} className="mt-4 space-y-4">
                        <div>
                            <label htmlFor="settings-current-password" className={labelCls}>当前密码</label>
                            <input id="settings-current-password" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className={inputCls} placeholder="输入当前密码" />
                        </div>
                        <div>
                            <label htmlFor="settings-new-password" className={labelCls}>新密码</label>
                            <input id="settings-new-password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={inputCls} placeholder="输入新密码" />
                        </div>
                        <div>
                            <label htmlFor="settings-confirm-password" className={labelCls}>确认新密码</label>
                            <input id="settings-confirm-password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className={inputCls} placeholder="再次输入新密码" />
                        </div>
                        <button type="submit" disabled={saving || !currentPassword || !newPassword} className={btnCls}>
                            {saving ? '修改中…' : '修改密码'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}
