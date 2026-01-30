/**
 * 教学域类型定义
 */

export type AttemptStatus = 'in_progress' | 'completed' | 'graded' | 'abandoned'

export interface Assignment {
  id: number
  classId: number
  courseId?: number | null
  title: string
  sopId?: number | null
  guidancePolicyId?: number | null
  startAt?: string | null
  dueAt?: string | null
  maxAttempts?: number | null
  scoringPolicy?: Record<string, unknown> | null
  competitionMode?: boolean
  hiddenSop?: boolean
  blindStepMask?: Record<string, unknown> | null
  createdAt?: string
  updatedAt?: string
}

export interface AssignmentAttempt {
  id: number
  assignmentId: number
  studentId: number
  taskId?: number | null
  evidenceBundleId?: string | null
  status: AttemptStatus
  score?: number | null
  attemptIndex: number
  diagnosisCode?: string | null
  pathScore?: number | null
  evidenceQualityScore?: number | null
  createdAt?: string
  updatedAt?: string
}

export interface AttemptEvidenceSummary {
  total_steps?: number
  skip_count?: number
  error_count?: number
  duration_ms?: number
  [key: string]: unknown
}

export interface AttemptEvidenceResponse {
  bundleId: string
  taskId?: number | null
  attemptId: number
  summary?: AttemptEvidenceSummary | null
}

export type DiagnosisSeverity = 'LOW' | 'MEDIUM' | 'HIGH'

export interface DiagnosisSourceRefs {
  attemptEvidenceId: number
}

export interface DiagnosisReport {
  reportVersion: string
  attemptId: number
  diagnosisCode: string
  ruleId: string
  severity: DiagnosisSeverity
  findings: string[]
  recommendations: string[]
  generatedAt: string
  sourceRefs: DiagnosisSourceRefs
}
