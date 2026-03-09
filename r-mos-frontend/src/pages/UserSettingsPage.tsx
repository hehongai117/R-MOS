import { useState } from 'react'
import { PageHeader } from '@/components/common'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/api/client'

export default function UserSettingsPage() {
    const user = useAuthStore((state) => state.user)
    const [fullName, setFullName] = useState(user?.full_name ?? '')
    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [saving, setSaving] = useState(false)
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

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

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
                {/* Profile section */}
                <div className="rounded-lg border border-border-subtle p-6">
                    <h3 className="text-sm font-semibold text-text-primary">基本信息</h3>
                    <form onSubmit={(e) => void handleUpdateProfile(e)} className="mt-4 space-y-4">
                        <div>
                            <label className={labelCls}>邮箱</label>
                            <input type="email" value={user?.email ?? ''} disabled className={`${inputCls} opacity-60`} />
                        </div>
                        <div>
                            <label className={labelCls}>角色</label>
                            <input type="text" value={user?.role ?? ''} disabled className={`${inputCls} opacity-60`} />
                        </div>
                        <div>
                            <label className={labelCls}>姓名</label>
                            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputCls} placeholder="输入姓名" />
                        </div>
                        <button type="submit" disabled={saving} className={btnCls}>
                            {saving ? '保存中…' : '保存'}
                        </button>
                    </form>
                </div>

                {/* Password section */}
                <div className="rounded-lg border border-border-subtle p-6">
                    <h3 className="text-sm font-semibold text-text-primary">修改密码</h3>
                    <form onSubmit={(e) => void handleChangePassword(e)} className="mt-4 space-y-4">
                        <div>
                            <label className={labelCls}>当前密码</label>
                            <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className={inputCls} placeholder="输入当前密码" />
                        </div>
                        <div>
                            <label className={labelCls}>新密码</label>
                            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={inputCls} placeholder="输入新密码" />
                        </div>
                        <div>
                            <label className={labelCls}>确认新密码</label>
                            <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className={inputCls} placeholder="再次输入新密码" />
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
