import {
  CheckCircle2,
  ClipboardList,
  FileSearch,
  History,
  Rocket,
  ShieldCheck,
} from 'lucide-react'

export interface IntentOption {
  value: string
  label: string
}

export interface QuickAction {
  id: string
  title: string
  desc: string
  prompt: string
  intent: string
  icon: typeof Rocket
}

export const INTENT_OPTIONS: IntentOption[] = [
  { value: 'general', label: '通用问答' },
  { value: 'execute-task', label: '派单维保' },
  { value: 'delegate-diagnoser', label: '诊断问题' },
  { value: 'read-kb', label: '知识查询' },
  { value: 'write-kb', label: '知识记录' },
  { value: 'delegate-coach', label: '训练指导' },
]

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'dispatch',
    title: '派单维保',
    desc: '创建维保任务与执行步骤',
    prompt: '请为我创建一个维保派单，并给出执行步骤。',
    intent: 'execute-task',
    icon: Rocket,
  },
  {
    id: 'diagnose',
    title: '诊断问题',
    desc: '分析设备异常与根因',
    prompt: '请帮我诊断当前设备异常并给出排查建议。',
    intent: 'delegate-diagnoser',
    icon: FileSearch,
  },
  {
    id: 'kb',
    title: '知识查询',
    desc: '检索 SOP 与操作知识',
    prompt: '查询减速器相关 SOP 和注意事项。',
    intent: 'read-kb',
    icon: ShieldCheck,
  },
  {
    id: 'tasks',
    title: '查看任务',
    desc: '汇总当前执行上下文',
    prompt: '查看我当前进行中的任务和状态。',
    intent: 'general',
    icon: ClipboardList,
  },
  {
    id: 'approvals',
    title: '审批待办',
    desc: '检查待审批项与风险等级',
    prompt: '查看当前待审批项，并说明每项风险等级。',
    intent: 'general',
    icon: CheckCircle2,
  },
  {
    id: 'reports',
    title: '查看报告',
    desc: '输出执行总结与问题报告',
    prompt: '生成今天的执行总结和问题报告。',
    intent: 'general',
    icon: History,
  },
]

export const RISK_STATUS_MAP: Record<string, 'success' | 'warning' | 'error'> = {
  R0: 'success',
  R1: 'success',
  R2: 'warning',
  R3: 'error',
}
