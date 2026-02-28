// Agent API Client
// P0: Frontend integration for Agent services

import client from './client';

// Types matching backend services

export interface AgentRequest {
  request_id?: string;
  user_id: string;
  message: string;
  context?: Record<string, any>;
}

export interface AgentResponse {
  response_id: string;
  request_id: string;
  message: string;
  action_suggested?: Record<string, any>;
  confidence: number;
  evidence_refs: string[];
}

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
  risk_events: Record<string, any>[];
  confidence: number;
}

export interface DiagnoserOutput {
  root_cause?: string;
  root_cause_confidence: number;
  evidence_refs: string[];
  intervention?: Record<string, any>;
  baseline_comparison?: Record<string, any>;
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

// Agent Orchestrator API

export const sendAgentRequest = async (request: AgentRequest): Promise<AgentResponse> => {
  const response = await client.post<AgentResponse>('/agent/request', request);
  return response.data;
};

export const getTaskStatus = async (userId: string): Promise<Record<string, any>> => {
  const response = await client.get<Record<string, any>>(`/agent/task-status/${userId}`);
  return response.data;
};

// Coach Agent API

export const getCoachRecommendation = async (
  taskId: string,
  currentStep: number,
  stepHistory: Record<string, any>[],
  traineeAction?: Record<string, any>
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
  errorHistory: Record<string, any>[],
  actionHistory: Record<string, any>[],
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
  scope?: Record<string, any>;
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

// Multi-Agent Coordination API

export const coordinateAgents = async (
  taskId: string,
  userId: string,
  action: string,
  context: Record<string, any>
): Promise<Record<string, any>> => {
  const response = await client.post<Record<string, any>>('/agent/coordinate', {
    task_id: taskId,
    user_id: userId,
    action,
    context,
  });
  return response.data;
};

// Evidence Enforcement API

export const getEvidenceStatus = async (stepId: string): Promise<Record<string, any>> => {
  const response = await client.get<Record<string, any>>(`/agent/evidence/status/${stepId}`);
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
