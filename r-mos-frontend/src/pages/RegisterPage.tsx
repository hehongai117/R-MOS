import { Bot, CheckCircle, LoaderCircle, UserPlus } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import axios from 'axios'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

interface RegisterResponse {
    user_id: number
    email: string
    message: string
}

function RegisterPage() {
    const navigate = useNavigate()
    const [fullName, setFullName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isSuccess, setIsSuccess] = useState(false)

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()

        if (password !== confirmPassword) {
            toast.error('两次输入的密码不一致')
            return
        }

        if (password.length < 8) {
            toast.error('密码长度至少 8 位')
            return
        }

        setIsLoading(true)

        try {
            await axios.post<RegisterResponse>(
                `${API_BASE_URL}/api/v1/auth/register`,
                { email, password, full_name: fullName },
            )
            setIsSuccess(true)
            toast.success('注册成功！请登录')
            setTimeout(() => navigate('/login'), 2000)
        } catch (error) {
            if (axios.isAxiosError(error) && error.response?.data) {
                const msg =
                    (error.response.data as { message?: string }).message ??
                    '注册失败，请检查输入'
                toast.error(msg)
            } else {
                toast.error('注册失败，请稍后再试')
            }
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="relative flex min-h-screen items-center justify-center bg-bg-base px-4">
            {/* subtle background glow */}
            <div
                className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-15"
                style={{
                    background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)',
                }}
            />

            <div className="relative z-10 w-full max-w-[440px] overflow-hidden rounded-2xl border border-border-subtle bg-bg-surface/80 shadow-lg backdrop-blur-sm">
                <div className="p-10">
                    {/* brand header */}
                    <div className="mb-8 flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
                            <Bot className="h-5 w-5 text-white" />
                        </div>
                        <div>
                            <p className="font-mono text-xl font-bold text-primary">R-MOS</p>
                            <p className="text-xs text-text-muted">Robot Maintenance OS</p>
                        </div>
                    </div>

                    {isSuccess ? (
                        <div className="space-y-4 py-8 text-center animate-fade-in">
                            <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
                            <p className="text-lg font-semibold text-text-primary">注册成功</p>
                            <p className="text-sm text-text-secondary">
                                正在跳转到登录页面...
                            </p>
                        </div>
                    ) : (
                        <>
                            <div className="mb-6">
                                <p className="text-xl font-semibold text-text-primary">创建账户</p>
                                <p className="mt-1 text-sm text-text-secondary">
                                    注册 R-MOS 账户以开始使用
                                </p>
                            </div>

                            <form className="space-y-4" onSubmit={handleSubmit}>
                                <div className="space-y-1.5">
                                    <label
                                        className="text-xs font-medium uppercase tracking-wider text-text-muted"
                                        htmlFor="register-name"
                                    >
                                        姓名
                                    </label>
                                    <Input
                                        autoComplete="name"
                                        id="register-name"
                                        name="fullName"
                                        placeholder="您的姓名"
                                        required
                                        type="text"
                                        value={fullName}
                                        onChange={(e) => setFullName(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label
                                        className="text-xs font-medium uppercase tracking-wider text-text-muted"
                                        htmlFor="register-email"
                                    >
                                        邮箱地址
                                    </label>
                                    <Input
                                        autoComplete="email"
                                        id="register-email"
                                        name="email"
                                        placeholder="user@rmos.io"
                                        required
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label
                                        className="text-xs font-medium uppercase tracking-wider text-text-muted"
                                        htmlFor="register-password"
                                    >
                                        密码
                                    </label>
                                    <Input
                                        autoComplete="new-password"
                                        id="register-password"
                                        name="password"
                                        placeholder="至少 8 位，含大小写和数字"
                                        required
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label
                                        className="text-xs font-medium uppercase tracking-wider text-text-muted"
                                        htmlFor="register-confirm"
                                    >
                                        确认密码
                                    </label>
                                    <Input
                                        autoComplete="new-password"
                                        id="register-confirm"
                                        name="confirmPassword"
                                        placeholder="再次输入密码"
                                        required
                                        type="password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                    />
                                </div>

                                <Button className="w-full" disabled={isLoading} type="submit">
                                    {isLoading ? (
                                        <>
                                            <LoaderCircle className="h-4 w-4 animate-spin" />
                                            注册中...
                                        </>
                                    ) : (
                                        <>
                                            <UserPlus className="h-4 w-4" />
                                            注册
                                        </>
                                    )}
                                </Button>
                            </form>

                            <div className="mt-6 text-center text-sm text-text-secondary">
                                已有账户？{' '}
                                <Link
                                    className="text-primary underline-offset-4 hover:underline"
                                    to="/login"
                                >
                                    返回登录
                                </Link>
                            </div>
                        </>
                    )}
                </div>

                <div className="border-t border-border-subtle px-10 py-3 text-center text-xs text-text-muted">
                    © 2026 R-MOS · v0.2.0
                </div>
            </div>
        </div>
    )
}

export default RegisterPage
