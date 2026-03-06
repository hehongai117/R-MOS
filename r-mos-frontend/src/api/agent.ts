// Agent API Client
// P0: Frontend integration for Agent services

import client from './client';

// Types matching backend services

export interface AgentRequest {
  request_id?: string;
  user_id: string;
  message: string;
  context?: Record<string, unknown>;
}

export interface AgentResponse {
  response_id: string;
  request_id: string;
  message: string;
  action_suggested?: Record<string, unknown>;
  confidence: number;
  evidence_refs: string[];
}

const isObjectRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const readString = (value: unknown, fallback: string): string =>
  typeof value === 'string' ? value : fallback;

const readNumber = (value: unknown, fallback: number): number =>
  typeof value === 'number' ? value : fallback;

const readStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

export interface NextAction {
  action_id: string;
  action_type: string;
  target?: string;
  explanation: string;
  risk_level: string;
  evidence_required: string[];
}

export interface CoachOutput {
  next_action?: NextAction;
  explanation: string;
  risk_events: Record<string, unknown>[];
  confidence: number;
}

export interface DiagnoserOutput {
  root_cause?: string;
  root_cause_confidence: number;
  evidence_refs: string[];
  intervention?: Record<string, unknown>;
  baseline_comparison?: Record<string, unknown>;
}

export interface KnowledgeEntry {
  id: string;
  type: string;
  status: string;
  title: string;
  content: string;
  scope?: {
    device_model: string[];
    part_type: string[];
    version_range?: string;
    scenario: string[];
  };
  contraindications?: {
    device_model: string[];
    part_material: string[];
    conditions: string[];
  };
  risk_level: string;
  confidence?: {
    evidence_count: number;
    success_rate: number;
    reviewer_count: number;
  };
  created_at: number;
  created_by: string;
}

export interface KnowledgeUploadJob {
  job_id: string
  status: string
  filename?: string
  content_type?: string
  size_bytes?: number
  brand?: string | null
}

// Agent Orchestrator API

export const sendAgentRequest = async (request: AgentRequest): Promise<AgentResponse> => {
  // P2-1: Use unified /agent/execute endpoint (message mode)
  const response = await client.post<AgentExecuteResponse>('/agent/execute', {
    user_id: request.user_id,
    mode: 'message',
    message: request.message,
    context: request.context,
  });

  // Convert to legacy response format for backward compatibility
  const data = response.data;
  const result = isObjectRecord(data.result) ? data.result : {};
  const messageFromResult = readString(result.message, readString(result.response, JSON.stringify(result)));
  const actionSuggested = isObjectRecord(result.action) ? result.action : undefined;
  return {
    response_id: data.trace_id,
    request_id: request.request_id || data.trace_id,
    message: messageFromResult,
    action_suggested: actionSuggested,
    confidence: readNumber(result.confidence, 0.9),
    evidence_refs: readStringArray(result.evidence_refs),
  };
};

export const getTaskStatus = async (userId: string): Promise<Record<string, unknown>> => {
  const response = await client.get<Record<string, unknown>>(`/agent/task-status/${userId}`);
  return response.data;
};

// Coach Agent API

export const getCoachRecommendation = async (
  taskId: string,
  currentStep: number,
  stepHistory: Record<string, unknown>[],
  traineeAction?: Record<string, unknown>
): Promise<CoachOutput> => {
  const response = await client.post<CoachOutput>('/agent/coach/recommend', {
    task_id: taskId,
    current_step: currentStep,
    step_history: stepHistory,
    trainee_action: traineeAction,
  });
  return response.data;
};

// Diagnoser Agent API

export const diagnoseError = async (
  taskId: string,
  errorHistory: Record<string, unknown>[],
  actionHistory: Record<string, unknown>[],
  evidenceRefs: string[]
): Promise<DiagnoserOutput> => {
  const response = await client.post<DiagnoserOutput>('/agent/diagnoser/diagnose', {
    task_id: taskId,
    error_history: errorHistory,
    action_history: actionHistory,
    evidence_refs: evidenceRefs,
  });
  return response.data;
};

// Knowledge Governance API

export const searchKnowledge = async (query: {
  query?: string;
  device_model?: string;
  part_type?: string;
  status?: string;
}): Promise<{ results: KnowledgeEntry[] }> => {
  const response = await client.post<{ results: KnowledgeEntry[] }>('/agent/knowledge/search', query);
  return response.data;
};

export const createKnowledge = async (data: {
  title: string;
  content: string;
  type: string;
  scope?: Record<string, unknown>;
  risk_level?: string;
}): Promise<KnowledgeEntry> => {
  const response = await client.post<KnowledgeEntry>('/agent/knowledge', data);
  return response.data;
};

export const submitKnowledgeForReview = async (entryId: string): Promise<void> => {
  await client.post(`/agent/knowledge/${entryId}/submit`);
};

export const approveKnowledge = async (
  entryId: string,
  decision: 'approve' | 'reject',
  feedback?: string
): Promise<void> => {
  await client.post(`/agent/knowledge/${entryId}/approve`, {
    decision,
    feedback,
  });
};

export const uploadKnowledgeFile = async (file: File, brand?: string): Promise<KnowledgeUploadJob> => {
  const formData = new FormData()
  formData.append('file', file)
  if (brand) {
    formData.append('brand', brand)
  }
  const response = await client.post<KnowledgeUploadJob>('/agent/knowledge/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const getKnowledgeUploadJob = async (jobId: string): Promise<KnowledgeUploadJob> => {
  const response = await client.get<KnowledgeUploadJob>(`/agent/knowledge/upload/${jobId}`)
  return response.data
}

// Multi-Agent Coordination API

export const coordinateAgents = async (
  taskId: string,
  userId: string,
  action: string,
  context: Record<string, unknown>
): Promise<Record<string, unknown>> => {
  const response = await client.post<Record<string, unknown>>('/agent/coordinate', {
    task_id: taskId,
    user_id: userId,
    action,
    context,
  });
  return response.data;
};

// Evidence Enforcement API

export const getEvidenceStatus = async (stepId: string): Promise<Record<string, unknown>> => {
  const response = await client.get<Record<string, unknown>>(`/agent/evidence/status/${stepId}`);
  return response.data;
};

export const collectEvidence = async (
  stepId: string,
  evidenceId: string,
  evidenceType: string
): Promise<void> => {
  await client.post('/agent/evidence/collect', {
    step_id: stepId,
    evidence_id: evidenceId,
    evidence_type: evidenceType,
  });
};

export const canProceedToNextStep = async (stepId: string): Promise<{ allowed: boolean; reason: string }> => {
  const response = await client.get<{ allowed: boolean; reason: string }>(`/agent/evidence/can-proceed/${stepId}`);
  return response.data;
};

// ============ P2-1: Unified Agent Execute API ============

export type AgentExecuteMode = 'command' | 'message' | 'auto';

export interface AgentExecuteRequest {
  // Common
  user_id: string;
  mode?: AgentExecuteMode;

  // Command mode fields
  intent?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  skill_id?: string;
  side_effects?: string[];
  input_text?: string;

  // Message mode fields
  message?: string;

  // Shared fields
  context?: Record<string, unknown>;
  resource_ref?: Record<string, unknown>;
  policy_context?: Record<string, unknown>;
  intent_classification?: string;
  trace_id?: string;
  idempotency_key?: string;
}

export interface AgentExecuteResponse {
  status: 'success' | 'pending_approval' | 'error';
  result?: Record<string, unknown>;
  trace_id: string;
  from_cache: boolean;
  approval_id?: number;
  mode_used: 'command' | 'message';
}

/**
 * Unified Agent Execute API - P2-1 Convergence
 *
 * Replaces both:
 * - POST /ai/commands (Command mode)
 * - POST /agent/v2/request (Message mode)
 *
 * Auto-detects mode if not specified.
 */
export const agentExecute = async (request: AgentExecuteRequest): Promise<AgentExecuteResponse> => {
  const response = await client.post<AgentExecuteResponse>('/agent/execute', request);
  return response.data;
};
