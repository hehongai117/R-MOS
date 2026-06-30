/**
 * aiPipelineRobustness.test.ts — Phase 4 Task A4
 *
 * 审计结论：所有 AI 调用点均有 loading 态 + 全局拦截器 message.error 托底，
 * 错误可见性已覆盖。唯一真实缺口：
 *   1. sendAgentRequestV2（多 Agent 编排 + LLM 诊断）— 全局 30s 超时不足
 *   2. sendAIChat（AI 助手对话）— 与 askTrainingWorkbenchAssistant 同类 LLM 调用，
 *      后者已设 90s，前者漏设
 * 修复方式：在各自调用点传 { timeout: 90000 }，不修改全局默认值。
 *
 * TDD 流程：先写失败测试（RED）→ 实现 → 绿（GREEN）
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Mock the axios client BEFORE any module under test is imported.
// Both `client` (default export) and `apiClient` (named export) from
// '../client' are the same axios instance — expose a single mock object for
// both so we can inspect every post() invocation regardless of which binding
// the module uses.
// ---------------------------------------------------------------------------
vi.mock('../client', () => {
  const mockClient = {
    post: vi.fn(),
    get: vi.fn(),
  }
  return {
    default: mockClient,
    apiClient: mockClient,
  }
})

// Imports must come AFTER vi.mock (vitest hoists vi.mock automatically)
import client from '../client'
import { sendAgentRequestV2 } from '../agent-v2'
import { sendAIChat } from '../aiAssistant'

const mockPost = vi.mocked(client.post)

beforeEach(() => {
  vi.clearAllMocks()
})

// ---------------------------------------------------------------------------
// Helper — minimal successful response shape for sendAgentRequestV2
// ---------------------------------------------------------------------------
const agentSuccessResponse = {
  data: {
    status: 'success' as const,
    result: {
      success: true,
      trace_id: 'trace-test',
      message: 'ok',
      confidence: '0.9',
      evidence_refs: [] as string[],
      from_cache: false,
      timestamp: 1_700_000_000_000,
    },
    trace_id: 'trace-test',
    from_cache: false,
    mode_used: 'message' as const,
  },
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AI pipeline robustness — timeout guards (Task A4)', () => {
  // -------------------------------------------------------------------------
  // sendAgentRequestV2
  // -------------------------------------------------------------------------
  describe('sendAgentRequestV2', () => {
    it(
      'passes a per-call timeout ≥ 60 000 ms to protect against slow LLM orchestration ' +
        '[RED before fix, GREEN after adding { timeout: 90000 } to client.post call]',
      async () => {
        mockPost.mockResolvedValueOnce(agentSuccessResponse)

        await sendAgentRequestV2({ user_id: '1', message: 'diagnose' })

        // The function calls client.post(url, body, config?)
        // Verify the 3rd argument contains a timeout >= 60 000 ms
        const [, , config] = mockPost.mock.calls[0] as [
          string,
          unknown,
          { timeout?: number } | undefined,
        ]
        expect(config?.timeout).toBeGreaterThanOrEqual(60_000)
      },
    )

    it('propagates rejections so callers can surface them via message.error', async () => {
      mockPost.mockRejectedValueOnce(new Error('network error'))
      await expect(sendAgentRequestV2({ user_id: '1', message: 'test' })).rejects.toThrow()
    })
  })

  // -------------------------------------------------------------------------
  // sendAIChat
  // -------------------------------------------------------------------------
  describe('sendAIChat', () => {
    it(
      'passes a per-call timeout ≥ 60 000 ms to match askTrainingWorkbenchAssistant (90s) ' +
        '[RED before fix, GREEN after adding { timeout: 90000 } to apiClient.post call]',
      async () => {
        mockPost.mockResolvedValueOnce({
          data: { reply: '好的', hint_level_used: 1 },
        })

        await sendAIChat({ message: 'hello' })

        const [, , config] = mockPost.mock.calls[0] as [
          string,
          unknown,
          { timeout?: number } | undefined,
        ]
        expect(config?.timeout).toBeGreaterThanOrEqual(60_000)
      },
    )

    it('propagates rejections so AIAssistantPanel catch block can show error message', async () => {
      mockPost.mockRejectedValueOnce(new Error('timeout'))
      await expect(sendAIChat({ message: 'hello' })).rejects.toThrow()
    })
  })
})
