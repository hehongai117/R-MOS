/**
 * Agent V2 API Client
 * Unified SDK for Phase 1 agent features
 */

import client from './client';

// Types for V2 API (extended from agent.ts)

export interface ResourceRef {
  type: 'task' | 'sop' | 'knowledge' | 'robot' | 'user' | 'course' | 'assignment' | 'evidence';
  id: string;
  access: 'read' | 'write' | 'execute' | 'admin';
  scope?: 'personal' | 'course' | 'shared';
  owner_id?: string;
  metadata?: Record<string, unknown>;
}

export interface TelemetryJointState {
  joint_id: string;
  position: number;
  velocity: number;
  torque?: number;
  current?: number;
  temperature?: number;
  error_code?: string;
}

export interface TelemetrySensorData {
  imu?: {
    acceleration: { x: number; y: number; z: number };
    angular_velocity: { x: number; y: number; z: number };
    orientation?: { x: number; y: number; z: number; w: number };
  };
  battery?: number;
  temperature?: number;
  voltage?: Record<string, number>;
  pressure?: Record<string, number>;
}

export interface TelemetryPayload {
  joints: TelemetryJointState[];
  sensors: TelemetrySensorData;
  active_faults: string[];
}

export interface FaultHypothesis {
  fault_code: string;
  fault_name: string;
  confidence: number;
  affected_parts: string[];
  possible_causes: string[];
  evidence: Record<string, unknown>;
}

export interface DiagnosisResult {
  success: boolean;
  primary_hypothesis: FaultHypothesis | null;
  alternative_hypotheses: FaultHypothesis[];
  requires_supervisor: boolean;
  reasoning: string;
  recommended_actions: string[];
  error_message?: string | null;
}

export interface MaintenanceAction {
  action_id: string;
  action_type: string;
  target_part: string;
  description: string;
  estimated_duration_minutes: number;
  required_tools: string[];
  safety_warnings: string[];
}

export interface MaintenancePlan {
  success: boolean;
  plan_id: string;
  fault_code: string;
  fault_name: string;
  actions: MaintenanceAction[];
  total_duration_minutes: number;
  requires_supervisor: boolean;
  validation_required: boolean;
  error_message?: string | null;
}

export interface VerificationResult {
  success: boolean;
  plan_id: string;
  before_state: Record<string, unknown>;
  after_state: Record<string, unknown>;
  delta_summary: Record<string, unknown>;
  verdict: string;
  failed_steps: string[];
}

export interface AgentExecutionResult {
  status?: string;
  message?: string;
  diagnosis?: DiagnosisResult | null;
  maintenance_plan?: MaintenancePlan | null;
  verification?: VerificationResult | null;
  trace_id?: string;
  action?: Record<string, unknown>;
}

export interface AgentRequestV2 {
  user_id: string;
  message: string;
  context?: Record<string, unknown>;
  telemetry_payload?: TelemetryPayload;
  resource_ref?: {
    resources?: ResourceRef[];
    resource?: ResourceRef;
  };
  policy_context?: Record<string, unknown>;
  intent_classification?: string;
  trace_id?: string;
  idempotency_key?: string;
}

export interface AgentResponseV2 {
  success: boolean;
  trace_id: string;
  message: string;
  result?: AgentExecutionResult;
  action_suggested?: Record<string, unknown>;
  confidence: string;
  evidence_refs: string[];
  policy_decision?: {
    allowed: boolean;
    risk_level: 'R0' | 'R1' | 'R2' | 'R3';
    requires_approval: boolean;
    approval_level?: string;
    evidence_required: string[];
  };
  from_cache: boolean;
  timestamp: number;
  error?: string;
}

export interface TaskContext {
  task_id: string;
  trace_id: string;
  state: string;
  user_id: string;
  skill_id?: string;
  current_step: number;
  total_steps: number;
  budget_used_ms: number;
  budget_limit_ms: number;
  created_at: number;
  started_at?: number;
  completed_at?: number;
}

export interface PolicyDecision {
  allowed: boolean;
  risk_level: 'R0' | 'R1' | 'R2' | 'R3';
  requires_approval: boolean;
  approval_level?: string;
  evidence_required: string[];
  conditions?: Record<string, unknown>;
  warnings?: string[];
  matched_rules?: string[];
}

export interface ModuleInfo {
  id: string;
  metadata: {
    name: string;
    description?: string;
    [key: string]: unknown;
  };
}

// ============ V2 API Endpoints ============

/**
 * Send agent request with full resource binding support (OrchestratorV2)
 */
export const sendAgentRequestV2 = async (request: AgentRequestV2): Promise<AgentResponseV2> => {
  const response = await client.post<{
    status: 'success' | 'pending_approval' | 'error';
    result?: AgentResponseV2;
    trace_id: string;
    from_cache: boolean;
    approval_id?: number;
    mode_used: 'command' | 'message';
  }>('/agent/execute', { ...request, mode: 'message' });

  const payload = response.data;
  const result = payload.result;

  if (payload.status === 'error' || !result) {
    throw new Error('Agent request failed');
  }

  if (result.success === false) {
    throw new Error(result.error || 'Agent request denied');
  }

  return {
    ...result,
    trace_id: result.trace_id || payload.trace_id,
    from_cache: result.from_cache ?? payload.from_cache,
  };
};

/**
 * Create a new task with FSM
 */
export const createTaskV2 = async (
  userId: string,
  skillId?: string,
  budgetLimitMs: number = 300000
): Promise<{
  task_id: string;
  trace_id: string;
  state: string;
  budget_limit_ms: number;
}> => {
  const response = await client.post<{
    task_id: string;
    trace_id: string;
    state: string;
    budget_limit_ms: number;
  }>('/agent/v2/task/create', null, {
    params: { user_id: userId, skill_id: skillId, budget_limit_ms: budgetLimitMs }
  });
  return response.data;
};

/**
 * Transition task state
 */
export const transitionTaskState = async (
  taskId: string,
  event: string
): Promise<{
  task_id: string;
  state: string;
  message: string;
}> => {
  const response = await client.post<{
    task_id: string;
    state: string;
    message: string;
  }>(`/agent/v2/task/${taskId}/transition`, null, {
    params: { event }
  });
  return response.data;
};

/**
 * Get task status
 */
export const getTaskStatusV2 = async (taskId: string): Promise<TaskContext> => {
  const response = await client.get<TaskContext>(`/agent/v2/task/${taskId}`);
  return response.data;
};

/**
 * Evaluate policy for an action
 */
export const evaluatePolicyV2 = async (
  action: string,
  context: Record<string, unknown>
): Promise<PolicyDecision> => {
  const response = await client.post<PolicyDecision>('/agent/v2/policy/evaluate', {
    action,
    context,
  });
  return response.data;
};

/**
 * Get trace events for replay
 */
export const getTraceEvents = async (traceId: string): Promise<{
  trace_id: string;
  events: Record<string, unknown>[];
}> => {
  const response = await client.get<{
    trace_id: string;
    events: Record<string, unknown>[];
  }>(`/agent/v2/trace/${traceId}/events`);
  return response.data;
};

/**
 * List available modules
 */
export const listModules = async (): Promise<{ modules: ModuleInfo[] }> => {
  const response = await client.get<{ modules: ModuleInfo[] }>('/agent/v2/modules');
  return response.data;
};

// ============ Replay and Decision Recalculation APIs ============

export interface DecisionRecord {
  decision_id: string;
  decision_type: string;
  trace_id: string;
  timestamp: number;
  input_context: Record<string, unknown>;
  decision_result: Record<string, unknown>;
  risk_level: string;
  policy_rules_matched: string[];
  approved_by?: string;
}

export interface RecalculateRequest {
  original_decision_id: string;
  modified_params?: Record<string, unknown>;
  include_diff?: boolean;
}

export interface RecalculateResult {
  request_id: string;
  original_decision_id?: string;
  status: string;
  recalculated_result: Record<string, unknown>;
  diff?: {
    input_diffs: Array<{
      param: string;
      original: unknown;
      new: unknown;
      impact: string;
    }>;
    result_comparison: {
      original_risk: string;
      recalculated_risk: string;
      decision_changed: boolean;
    };
  };
  recalculated_at: number;
  error?: string;
}

export interface TraceReplay {
  trace_id: string;
  events: Record<string, unknown>[];
  decisions: DecisionRecord[];
  evidence: Record<string, unknown>;
  event_count: number;
  decision_count: number;
}

/**
 * Record a decision for future replay
 */
export const recordDecision = async (request: {
  decision_type: string;
  trace_id: string;
  input_context: Record<string, unknown>;
  decision_result: Record<string, unknown>;
  risk_level: string;
  policy_rules_matched?: string[];
  approved_by?: string;
}): Promise<{ decision_id: string; status: string }> => {
  const response = await client.post<{ decision_id: string; status: string }>(
    '/agent/replay/decision/record',
    request
  );
  return response.data;
};

/**
 * Get a recorded decision
 */
export const getDecision = async (decisionId: string): Promise<DecisionRecord> => {
  const response = await client.get<DecisionRecord>(`/agent/replay/decision/${decisionId}`);
  return response.data;
};

/**
 * Get all decisions for a trace
 */
export const getTraceDecisions = async (traceId: string): Promise<{
  trace_id: string;
  decisions: Array<{
    decision_id: string;
    decision_type: string;
    timestamp: number;
    risk_level: string;
  }>;
}> => {
  const response = await client.get<{
    trace_id: string;
    decisions: Array<{
      decision_id: string;
      decision_type: string;
      timestamp: number;
      risk_level: string;
    }>;
  }>(`/agent/replay/trace/${traceId}/decisions`);
  return response.data;
};

/**
 * Recalculate a decision with modified parameters
 */
export const recalculateDecision = async (request: RecalculateRequest): Promise<RecalculateResult> => {
  const response = await client.post<RecalculateResult>('/agent/replay/recalculate', request);
  return response.data;
};

/**
 * Get recalculation history
 */
export const getRecalculationHistory = async (decisionId?: string, limit: number = 100): Promise<{
  recalculations: Array<{
    request_id: string;
    original_decision_id?: string;
    status: string;
    recalculated_at: number;
    error?: string;
  }>;
}> => {
  const response = await client.get<{
    recalculations: Array<{
      request_id: string;
      original_decision_id?: string;
      status: string;
      recalculated_at: number;
      error?: string;
    }>;
  }>('/agent/replay/recalculations', {
    params: { decision_id: decisionId, limit }
  });
  return response.data;
};

/**
 * Replay a full trace with all events, decisions, and evidence
 */
export const replayTrace = async (request: {
  trace_id: string;
  include_events?: boolean;
  include_decisions?: boolean;
  include_evidence?: boolean;
  start_ts_ms?: number;
  end_ts_ms?: number;
}): Promise<TraceReplay> => {
  const response = await client.post<TraceReplay>('/agent/replay/trace', request);
  return response.data;
};

// ============ Acceptance Metrics APIs ============

export interface MetricRecord {
  metric_id: string;
  name: string;
  category: string;
  target_value: number;
  actual_value: number;
  status: string;
  details?: Record<string, unknown>;
  description?: string;
  timestamp?: number;
}

export interface AcceptanceReport {
  report_id: string;
  timestamp: number;
  total_metrics: number;
  passed: number;
  failed: number;
  warnings: number;
  recommendation: string;
  metrics: MetricRecord[];
}

/**
 * Record a metric event
 */
export const recordMetricEvent = async (request: {
  metric_type: string;
  entry_id?: string;
  has_object_binding?: boolean;
  is_replayable?: boolean;
  is_unauthorized?: boolean;
}): Promise<{ status: string }> => {
  const response = await client.post<{ status: string }>('/agent/metrics/record', request);
  return response.data;
};

/**
 * Get current metrics
 */
export const getCurrentMetrics = async (): Promise<{ metrics: MetricRecord[] }> => {
  const response = await client.get<{ metrics: MetricRecord[] }>('/agent/metrics');
  return response.data;
};

/**
 * Get specific metric
 */
export const getSpecificMetric = async (metricId: string): Promise<MetricRecord> => {
  const response = await client.get<MetricRecord>(`/agent/metrics/${metricId}`);
  return response.data;
};

/**
 * Generate acceptance report
 */
export const generateAcceptanceReport = async (): Promise<AcceptanceReport> => {
  const response = await client.post<AcceptanceReport>('/agent/metrics/report');
  return response.data;
};

/**
 * Get acceptance reports history
 */
export const getAcceptanceReports = async (limit: number = 10): Promise<{
  reports: Array<{
    report_id: string;
    timestamp: number;
    total_metrics: number;
    passed: number;
    failed: number;
    warnings: number;
    recommendation: string;
  }>;
}> => {
  const response = await client.get<{
    reports: Array<{
      report_id: string;
      timestamp: number;
      total_metrics: number;
      passed: number;
      failed: number;
      warnings: number;
      recommendation: string;
    }>;
  }>('/agent/metrics/reports', { params: { limit } });
  return response.data;
};

/**
 * Reset metric counters
 */
export const resetMetrics = async (): Promise<{ status: string }> => {
  const response = await client.post<{ status: string }>('/agent/metrics/reset');
  return response.data;
};

// ============ Approval Queue APIs ============

export interface ApprovalRequest {
  id: string;
  requester_id: string;
  resource_type: string;
  resource_id: string;
  action: string;
  priority: string;
  reason: string;
  evidence_refs: string[];
  created_at: number;
  expires_at?: number;
  approved_by?: string;
  approved_at?: number;
  rejection_reason?: string;
}

/**
 * Get pending approval requests
 */
export const getPendingApprovals = async (priority?: string, limit: number = 100): Promise<{
  requests: ApprovalRequest[];
}> => {
  const response = await client.get<{ requests: ApprovalRequest[] }>('/agent/approval/pending', {
    params: { priority, limit }
  });
  return response.data;
};

/**
 * Get approval request history (approved/rejected)
 */
export const getApprovalHistory = async (limit: number = 100, offset: number = 0): Promise<{
  requests: ApprovalRequest[];
}> => {
  const response = await client.get<{ requests: ApprovalRequest[] }>('/agent/approval/history', {
    params: { limit, offset }
  });
  return response.data;
};

/**
 * Approve an approval request
 */
export const approveRequest = async (requestId: string, approvedBy: string): Promise<{
  request_id: string;
  status: string;
  approved_by: string;
}> => {
  const response = await client.post<{
    request_id: string;
    status: string;
    approved_by: string;
  }>(`/agent/approval/${requestId}/approve`, null, {
    params: { approved_by: approvedBy }
  });
  return response.data;
};

/**
 * Reject an approval request
 */
export const rejectRequest = async (requestId: string, rejectionReason: string): Promise<{
  request_id: string;
  status: string;
}> => {
  const response = await client.post<{
    request_id: string;
    status: string;
  }>(`/agent/approval/${requestId}/reject`, null, {
    params: { rejection_reason: rejectionReason }
  });
  return response.data;
};

// Re-export existing types for backward compatibility
export type { AgentRequest, AgentResponse, NextAction, CoachOutput, DiagnoserOutput } from './agent';
export * from './agent';
