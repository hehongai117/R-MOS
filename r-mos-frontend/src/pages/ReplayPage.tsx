import { PlayCircle, RefreshCw, Search } from 'lucide-react'
import { useState } from 'react'
import { Descriptions, Modal, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { replayTrace } from '@/api/agent-v2'
import { EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface TraceEvent {
  event_id: string
  event_type: string
  timestamp: number
  payload: Record<string, unknown>
}

interface DecisionRecord {
  decision_id: string
  decision_type: string
  timestamp: number
  risk_level: string
  decision_result: Record<string, unknown>
}

interface TraceData {
  trace_id: string
  events: TraceEvent[]
  decisions: DecisionRecord[]
  evidence: Record<string, unknown>
  event_count: number
  decision_count: number
}

const isObjectRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const readString = (value: unknown, fallback: string): string =>
  typeof value === 'string' ? value : fallback

const readNumber = (value: unknown, fallback: number): number =>
  typeof value === 'number' ? value : fallback

function formatDateTime(ts: number) {
  return new Date(ts).toLocaleString('zh-CN')
}

function riskTone(level: string) {
  if (level === 'R3') return 'error'
  if (level === 'R2') return 'warning'
  if (level === 'R1') return 'active'
  return 'success'
}

const ReplayPage = () => {
  const [loading, setLoading] = useState(false)
  const [traceId, setTraceId] = useState('')
  const [traceData, setTraceData] = useState<TraceData | null>(null)
  const [selectedEvent, setSelectedEvent] = useState<TraceEvent | null>(null)
  const [selectedDecision, setSelectedDecision] = useState<DecisionRecord | null>(null)

  const loadTrace = async () => {
    if (!traceId.trim()) return
    setLoading(true)
    try {
      const data = await replayTrace({
        trace_id: traceId,
        include_events: true,
        include_decisions: true,
        include_evidence: true,
      })

      const events = Array.isArray(data.events) ? data.events : []
      const decisions = Array.isArray(data.decisions) ? data.decisions : []
      setTraceData({
        trace_id: data.trace_id,
        events: events.map((evt: unknown, idx: number) => {
          const eventRecord = isObjectRecord(evt) ? evt : {}
          const payload = isObjectRecord(eventRecord.payload)
            ? eventRecord.payload
            : isObjectRecord(eventRecord.data)
              ? eventRecord.data
              : {}
          return {
            event_id: readString(eventRecord.event_id, readString(eventRecord.id, `evt-${idx}`)),
            event_type: readString(eventRecord.event_type, readString(eventRecord.type, 'unknown')),
            timestamp: readNumber(eventRecord.timestamp, Date.now()),
            payload,
          }
        }),
        decisions: decisions.map((dec: unknown, idx: number) => {
          const decisionRecord = isObjectRecord(dec) ? dec : {}
          const decisionResult = isObjectRecord(decisionRecord.decision_result)
            ? decisionRecord.decision_result
            : isObjectRecord(decisionRecord.result)
              ? decisionRecord.result
              : {}
          return {
            decision_id: readString(decisionRecord.decision_id, readString(decisionRecord.id, `dec-${idx}`)),
            decision_type: readString(decisionRecord.decision_type, readString(decisionRecord.type, 'unknown')),
            timestamp: readNumber(decisionRecord.timestamp, Date.now()),
            risk_level: readString(decisionRecord.risk_level, 'R0'),
            decision_result: decisionResult,
          }
        }),
        evidence: data.evidence || {},
        event_count: data.event_count,
        decision_count: data.decision_count,
      })
    } catch {
      setTraceData(null)
    } finally {
      setLoading(false)
    }
  }

  const eventColumns: ColumnsType<TraceEvent> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (ts: number) => formatDateTime(ts),
    },
    {
      title: '事件类型',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (value: string) => <StatusBadge label={value} status="pending" />,
    },
    {
      title: '事件 ID',
      dataIndex: 'event_id',
      key: 'event_id',
      render: (value: string) => <span className="font-mono text-xs text-text-secondary">{value}</span>,
    },
    {
      title: '摘要',
      dataIndex: 'payload',
      key: 'summary',
      render: (payload: Record<string, unknown>) => Object.keys(payload).slice(0, 2).map((key) => `${key}: ${String(payload[key])}`).join(', '),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: TraceEvent) => (
        <Button size="sm" type="button" variant="secondary" onClick={() => setSelectedEvent(record)}>
          详情
        </Button>
      ),
    },
  ]

  const decisionColumns: ColumnsType<DecisionRecord> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (ts: number) => formatDateTime(ts),
    },
    {
      title: '决策类型',
      dataIndex: 'decision_type',
      key: 'decision_type',
    },
    {
      title: '决策 ID',
      dataIndex: 'decision_id',
      key: 'decision_id',
      render: (value: string) => <span className="font-mono text-xs text-text-secondary">{value}</span>,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (value: string) => <StatusBadge label={value} status={riskTone(value)} />,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: DecisionRecord) => (
        <Button size="sm" type="button" variant="secondary" onClick={() => setSelectedDecision(record)}>
          详情
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['Agent', '执行回放']}
        subtitle="Trace 事件、决策与证据统一回放"
        title="执行回放"
      />

      <SectionCard title="Trace 查询">
        <div className="flex flex-wrap items-center gap-3">
          <Input
            className="max-w-[420px]"
            placeholder="输入 Trace ID 进行回放"
            value={traceId}
            onChange={(event) => setTraceId(event.target.value)}
          />
          <Button size="sm" type="button" onClick={() => void loadTrace()}>
            <PlayCircle className="h-4 w-4" />
            回放
          </Button>
          <Button size="sm" type="button" variant="secondary" onClick={() => void loadTrace()}>
            <RefreshCw className="h-4 w-4" />
            刷新
          </Button>
        </div>
      </SectionCard>

      {!traceData && !loading ? (
        <EmptyState
          description="请输入 Trace ID 开始回放。"
          icon={Search}
          title="等待回放请求"
        />
      ) : null}

      {traceData ? (
        <>
          <div className="grid gap-4 xl:grid-cols-3">
            <SectionCard title="Trace 摘要">
              <div className="space-y-3">
                <div className="font-mono text-text-primary">{traceData.trace_id}</div>
                <StatusBadge label={`事件 ${traceData.event_count}`} status="active" />
                <StatusBadge label={`决策 ${traceData.decision_count}`} status="warning" />
              </div>
            </SectionCard>
            <SectionCard title="事件列表">
              <div className="text-sm text-text-secondary">共 {traceData.event_count} 条事件</div>
            </SectionCard>
            <SectionCard title="证据摘要">
              <div className="text-xs text-text-muted">
                {Object.keys(traceData.evidence).length > 0
                  ? JSON.stringify(traceData.evidence)
                  : '暂无证据摘要'}
              </div>
            </SectionCard>
          </div>

          <SectionCard title="Trace 事件">
            <Table columns={eventColumns} dataSource={traceData.events} loading={loading} pagination={{ pageSize: 8 }} rowKey="event_id" />
          </SectionCard>

          <SectionCard title="决策记录">
            <Table columns={decisionColumns} dataSource={traceData.decisions} loading={loading} pagination={{ pageSize: 8 }} rowKey="decision_id" />
          </SectionCard>
        </>
      ) : null}

      <Modal footer={null} open={Boolean(selectedEvent)} title="事件详情" onCancel={() => setSelectedEvent(null)}>
        {selectedEvent ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="事件 ID">{selectedEvent.event_id}</Descriptions.Item>
            <Descriptions.Item label="事件类型">{selectedEvent.event_type}</Descriptions.Item>
            <Descriptions.Item label="时间">{formatDateTime(selectedEvent.timestamp)}</Descriptions.Item>
            <Descriptions.Item label="Payload">
              <pre className="whitespace-pre-wrap text-xs text-text-secondary">{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
            </Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>

      <Modal footer={null} open={Boolean(selectedDecision)} title="决策详情" onCancel={() => setSelectedDecision(null)}>
        {selectedDecision ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="决策 ID">{selectedDecision.decision_id}</Descriptions.Item>
            <Descriptions.Item label="决策类型">{selectedDecision.decision_type}</Descriptions.Item>
            <Descriptions.Item label="风险等级">{selectedDecision.risk_level}</Descriptions.Item>
            <Descriptions.Item label="时间">{formatDateTime(selectedDecision.timestamp)}</Descriptions.Item>
            <Descriptions.Item label="结果">
              <pre className="whitespace-pre-wrap text-xs text-text-secondary">{JSON.stringify(selectedDecision.decision_result, null, 2)}</pre>
            </Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </div>
  )
}

export default ReplayPage
