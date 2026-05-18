import { Bot, CheckCircle, ChevronLeft, ChevronRight, LoaderCircle, UserPlus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { debounce } from 'lodash-es'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { BRAND_NAME, COPYRIGHT_LINE } from '@/config/brand'
import { useAuthStore } from '@/store/authStore'
import { searchSchools, listSchoolTeachers, type SchoolItem, type TeacherItem } from '@/api/schools'

type Role = 'student' | 'teacher'

function RegisterPage() {
  const navigate = useNavigate()
  const registerAction = useAuthStore((s) => s.register)

  // 步骤控制
  const [step, setStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  // Step 1: 基本信息
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState<Role>('student')

  // Step 2: 学校
  const [schoolQuery, setSchoolQuery] = useState('')
  const [schoolOptions, setSchoolOptions] = useState<SchoolItem[]>([])
  const [selectedSchool, setSelectedSchool] = useState('')
  const [schoolSearching, setSchoolSearching] = useState(false)

  // Step 3: 教师选择（学生用）
  const [teachers, setTeachers] = useState<TeacherItem[]>([])
  const [selectedTeacherId, setSelectedTeacherId] = useState<number | null>(null)
  const [teachersLoading, setTeachersLoading] = useState(false)

  // 学校搜索（防抖）
  const debouncedSearch = useCallback(
    debounce(async (q: string) => {
      if (q.length < 2) {
        setSchoolOptions([])
        return
      }
      setSchoolSearching(true)
      try {
        const items = await searchSchools(q)
        setSchoolOptions(items)
      } catch {
        setSchoolOptions([])
      } finally {
        setSchoolSearching(false)
      }
    }, 300),
    [],
  )

  useEffect(() => {
    debouncedSearch(schoolQuery)
  }, [schoolQuery, debouncedSearch])

  // 选择学校后加载教师列表（仅学生）
  useEffect(() => {
    if (!selectedSchool || role !== 'student') return
    setTeachersLoading(true)
    listSchoolTeachers(selectedSchool)
      .then(setTeachers)
      .catch(() => setTeachers([]))
      .finally(() => setTeachersLoading(false))
  }, [selectedSchool, role])

  // Step 1 校验
  const canProceedStep1 =
    fullName.trim() && email.trim() && password.length >= 8 && password === confirmPassword

  // Step 2 校验
  const canProceedStep2 = !!selectedSchool

  // Step 3 校验（学生需选教师）
  const canSubmit = role === 'teacher' || !!selectedTeacherId

  const totalSteps = role === 'student' ? 3 : 2

  const handleNext = () => {
    if (step === 1 && !canProceedStep1) {
      if (password !== confirmPassword) toast.error('两次输入的密码不一致')
      else if (password.length < 8) toast.error('密码长度至少 8 位')
      return
    }
    if (step === 2 && role === 'teacher') {
      handleSubmit()
      return
    }
    setStep((s) => s + 1)
  }

  const handleSubmit = async () => {
    setIsLoading(true)
    try {
      const defaultRoute = await registerAction({
        email,
        password,
        full_name: fullName,
        role,
        school_name: selectedSchool,
        teacher_id: selectedTeacherId ?? undefined,
      })
      setIsSuccess(true)
      toast.success('注册成功！')
      setTimeout(() => navigate(defaultRoute), 1000)
    } catch (error: unknown) {
      const msg = (error as { response?: { data?: { message?: string } } })?.response?.data?.message ?? '注册失败'
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const stepTitle = ['基本信息', '选择学校', '选择教师'][step - 1]

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-bg-base px-4">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-15"
        style={{
          background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-[480px] overflow-hidden rounded-2xl border border-border-subtle bg-bg-surface/80 shadow-lg backdrop-blur-sm">
        <div className="p-10">
          {/* brand header */}
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-mono text-xl font-bold text-primary">{BRAND_NAME}</p>
              <p className="text-xs text-text-muted">Robot Maintenance OS</p>
            </div>
          </div>

          {isSuccess ? (
            <div className="space-y-4 py-8 text-center animate-fade-in">
              <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
              <p className="text-lg font-semibold text-text-primary">注册成功</p>
              <p className="text-sm text-text-secondary">正在跳转...</p>
            </div>
          ) : (
            <>
              {/* 步骤指示器 */}
              <div className="mb-6">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-xl font-semibold text-text-primary">{stepTitle}</p>
                  <span className="text-xs text-text-muted">步骤 {step}/{totalSteps}</span>
                </div>
                <div className="flex gap-1">
                  {Array.from({ length: totalSteps }, (_, i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        i < step ? 'bg-primary' : 'bg-border-subtle'
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Step 1: 基本信息 */}
              {step === 1 && (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted">角色</label>
                    <div className="flex gap-2">
                      {(['student', 'teacher'] as const).map((r) => (
                        <button
                          key={r}
                          type="button"
                          onClick={() => setRole(r)}
                          className={`flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                            role === r
                              ? 'border-primary bg-primary/10 text-primary'
                              : 'border-border-subtle text-text-secondary hover:border-text-muted'
                          }`}
                        >
                          {r === 'student' ? '学生' : '教师'}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-name">姓名</label>
                    <Input id="reg-name" placeholder="您的姓名" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-email">邮箱地址</label>
                    <Input id="reg-email" type="email" placeholder="user@rmos.io" required value={email} onChange={(e) => setEmail(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-pass">密码</label>
                    <Input id="reg-pass" type="password" placeholder="至少 8 位，含大小写和数字" required value={password} onChange={(e) => setPassword(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted" htmlFor="reg-confirm">确认密码</label>
                    <Input id="reg-confirm" type="password" placeholder="再次输入密码" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                  </div>
                </div>
              )}

              {/* Step 2: 学校选择 */}
              {step === 2 && (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wider text-text-muted">学校全称</label>
                    <Input
                      placeholder="输入学校名称搜索..."
                      value={schoolQuery}
                      onChange={(e) => {
                        setSchoolQuery(e.target.value)
                        setSelectedSchool('')
                      }}
                    />
                    {schoolSearching && <p className="text-xs text-text-muted">搜索中...</p>}
                  </div>
                  {schoolOptions.length > 0 && !selectedSchool && (
                    <div className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-border-subtle p-1">
                      {schoolOptions.map((s) => (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => {
                            setSelectedSchool(s.name)
                            setSchoolQuery(s.name)
                            setSchoolOptions([])
                          }}
                          className="w-full rounded-md px-3 py-2 text-left text-sm text-text-primary hover:bg-primary/10"
                        >
                          {s.name}
                          {s.province && <span className="ml-2 text-text-muted">({s.province})</span>}
                        </button>
                      ))}
                    </div>
                  )}
                  {selectedSchool && (
                    <div className="rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-primary">
                      已选择: {selectedSchool}
                    </div>
                  )}
                </div>
              )}

              {/* Step 3: 教师选择（仅学生） */}
              {step === 3 && role === 'student' && (
                <div className="space-y-4">
                  {teachersLoading ? (
                    <p className="text-sm text-text-muted">加载教师列表...</p>
                  ) : teachers.length === 0 ? (
                    <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-400">
                      该校暂无已注册教师，请联系教师先注册
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-sm text-text-secondary">请选择您的指导教师：</p>
                      {teachers.map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setSelectedTeacherId(t.id)}
                          className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                            selectedTeacherId === t.id
                              ? 'border-primary bg-primary/10'
                              : 'border-border-subtle hover:border-text-muted'
                          }`}
                        >
                          <p className="font-medium text-text-primary">{t.full_name || '未设置姓名'}</p>
                          <p className="text-xs text-text-muted">{t.email}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 导航按钮 */}
              <div className="mt-6 flex gap-3">
                {step > 1 && (
                  <Button variant="outline" onClick={() => setStep((s) => s - 1)} className="flex-1">
                    <ChevronLeft className="h-4 w-4" />
                    上一步
                  </Button>
                )}
                {step < totalSteps ? (
                  <Button
                    onClick={handleNext}
                    disabled={step === 1 ? !canProceedStep1 : !canProceedStep2}
                    className="flex-1"
                  >
                    下一步
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    onClick={role === 'teacher' ? handleNext : handleSubmit}
                    disabled={!canSubmit || isLoading}
                    className="flex-1"
                  >
                    {isLoading ? (
                      <>
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        注册中...
                      </>
                    ) : (
                      <>
                        <UserPlus className="h-4 w-4" />
                        完成注册
                      </>
                    )}
                  </Button>
                )}
              </div>

              <div className="mt-6 text-center text-sm text-text-secondary">
                已有账户？{' '}
                <Link className="text-primary underline-offset-4 hover:underline" to="/login">
                  返回登录
                </Link>
              </div>
            </>
          )}
        </div>

        <div className="border-t border-border-subtle px-10 py-3 text-center text-xs text-text-muted">
          {COPYRIGHT_LINE}
        </div>
      </div>
    </div>
  )
}

export default RegisterPage
