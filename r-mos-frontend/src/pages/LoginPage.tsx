import { LoaderCircle } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/store/authStore'

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
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="glass-card w-full max-w-[400px] rounded-xl p-8 animate-slide-up">
        <div className="mb-8">
          <p className="font-mono text-2xl text-primary">R-MOS</p>
          <p className="mt-2 text-sm text-text-secondary">机器人维护操作系统</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input
            autoComplete="email"
            name="email"
            placeholder="邮箱"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Input
            autoComplete="current-password"
            name="password"
            placeholder="密码"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
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

        <div className="mt-8 text-right text-xs text-text-muted">
          v0.1.0 · Frontend Redesign P1
        </div>
      </div>
    </div>
  )
}

export default LoginPage
