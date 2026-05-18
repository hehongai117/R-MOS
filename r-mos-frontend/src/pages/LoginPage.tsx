import { Bot, LoaderCircle, Shield, Wrench } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { BRAND_NAME, COPYRIGHT_LINE, APP_VERSION } from '@/config/brand'
import { useAuthStore } from '@/store/authStore'

/* ── animated grid background ── */

function GridBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* gradient grid overlay */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(45,125,210,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(45,125,210,0.5) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />
      {/* radial glow */}
      <div
        className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)',
        }}
      />
      {/* floating particles */}
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="absolute h-1 w-1 rounded-full bg-primary opacity-40"
          style={{
            left: `${15 + i * 14}%`,
            top: `${20 + (i % 3) * 25}%`,
            animation: `float-particle ${3 + i * 0.5}s ease-in-out infinite alternate`,
            animationDelay: `${i * 0.3}s`,
          }}
        />
      ))}
    </div>
  )
}

/* ── feature card ── */

function FeatureItem({ icon: Icon, label, desc }: { icon: typeof Bot; label: string; desc: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div>
        <div className="text-sm font-medium text-text-primary">{label}</div>
        <div className="text-xs text-text-muted">{desc}</div>
      </div>
    </div>
  )
}

/* ── main ── */

function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const defaultRoute = useAuthStore((state) => state.defaultRoute)
  const isInitialized = useAuthStore((state) => state.isInitialized)
  const isLoading = useAuthStore((state) => state.isLoading)
  const login = useAuthStore((state) => state.login)
  const user = useAuthStore((state) => state.user)

  useEffect(() => {
    if (isInitialized && user && defaultRoute) {
      navigate(defaultRoute, { replace: true })
    }
  }, [defaultRoute, isInitialized, navigate, user])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    try {
      const route = await login({ email, password })
      navigate(route, { replace: true })
    } catch (error) {
      const message =
        error instanceof Error ? error.message : '登录失败，请检查邮箱和密码'
      toast.error(message)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-bg-base px-4">
      <GridBackground />

      <div className="relative z-10 flex w-full max-w-[860px] overflow-hidden rounded-2xl border border-border-subtle shadow-lg">
        {/* ── Left: branding panel ── */}
        <div className="hidden w-[400px] shrink-0 flex-col justify-between bg-bg-surface/60 p-10 backdrop-blur-sm md:flex">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
                <Bot className="h-5 w-5 text-white" />
              </div>
              <div>
                <p className="font-mono text-xl font-bold text-primary">{BRAND_NAME}</p>
                <p className="text-xs text-text-muted">Robot Maintenance OS</p>
              </div>
            </div>

            <p className="mt-8 text-lg font-medium leading-relaxed text-text-primary">
              精密维保，<br />智能驱动。
            </p>
            <p className="mt-3 text-sm leading-6 text-text-secondary">
              一站式机器人维护操作系统，覆盖 SOP 管理、
              AI Agent 辅助决策、技能评估与教学闭环。
            </p>
          </div>

          <div className="space-y-4">
            <FeatureItem
              icon={Wrench}
              label="SOP 标准操作"
              desc="3D 可视化交互式维保流程"
            />
            <FeatureItem
              icon={Bot}
              label="AI Agent 决策"
              desc="智能审批、策略评估与轨迹回放"
            />
            <FeatureItem
              icon={Shield}
              label="技能成长体系"
              desc="五维画像、薄弱诊断与认证评估"
            />
          </div>

          <div className="pt-6 text-xs text-text-muted">
            {COPYRIGHT_LINE}
          </div>
        </div>

        {/* ── Right: login form ── */}
        <div className="flex flex-1 flex-col justify-center bg-bg-elevated/80 p-10 backdrop-blur-sm">
          {/* mobile-only brand header */}
          <div className="mb-8 md:hidden">
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              <span className="font-mono text-xl font-bold text-primary">{BRAND_NAME}</span>
            </div>
            <p className="mt-1 text-sm text-text-secondary">机器人维护操作系统</p>
          </div>

          <div className="mb-8 hidden md:block">
            <p className="text-xl font-semibold text-text-primary">欢迎回来</p>
            <p className="mt-1 text-sm text-text-secondary">
              请登录您的 R-MOS 账户以继续
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="login-email">
                邮箱地址
              </label>
              <Input
                autoComplete="email"
                id="login-email"
                name="email"
                placeholder="user@rmos.io"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="login-password">
                密码
              </label>
              <Input
                autoComplete="current-password"
                id="login-password"
                name="password"
                placeholder="••••••••"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            <Button className="w-full" disabled={isLoading} type="submit">
              {isLoading ? (
                <>
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  登录中...
                </>
              ) : (
                '登录'
              )}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-text-secondary">
            还没有账户？{' '}
            <Link
              className="text-primary underline-offset-4 hover:underline"
              to="/register"
            >
              立即注册
            </Link>
          </div>

          <div className="mt-8 text-right text-xs text-text-muted md:hidden">
            v{APP_VERSION}
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
