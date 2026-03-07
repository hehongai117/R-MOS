# P2-6: LLM Evaluation Metrics Specification
# P2-6: LLM 评测指标体系

Date: 2026-03-05
Phase: P2-6

## Five Evaluation Metrics

### 1. Intent Accuracy (意图准确率)
- **Definition**: Percentage of correctly identified user intents
- **Target**: > 90%
- **Calculation**: Correct intents / Total intents
- **Data Source**: audit_events table, belief_state

### 2. Decision Agreement Rate (裁决一致率)
- **Definition**: Percentage of agent decisions matching human expert decisions
- **Target**: > 85%
- **Calculation**: Matching decisions / Total decisions
- **Data Source**: approval_queue, audit_events

### 3. Knowledge Citation Precision (知识引用精度)
- **Definition**: Percentage of knowledge citations that are relevant and accurate
- **Target**: > 80%
- **Calculation**: Relevant citations / Total citations
- **Data Source**: audit_events, evidence_collector

### 4. P95 Latency (P95 延迟)
- **Definition**: 95th percentile response time for LLM calls
- **Target**: < 5 seconds
- **Calculation**: Percentile of response_times
- **Data Source**: audit_events.llm_latency_ms

### 5. Token Cost (Token 成本)
- **Definition**: Average token consumption per task
- **Target**: Monitor and optimize
- **Calculation**: Total tokens / Total tasks
- **Data Source**: audit_events.llm_token_count

## Metrics Collection

### Automated Collection Script
Location: `tests/eval/llm_metrics.py`

### Metrics Dashboard
Location: Frontend `/metrics` or `/admin/llm-metrics`

## Weekly Report Format

```
## LLM Evaluation Weekly Report

### Period: Week X (YYYY-MM-DD to YYYY-MM-DD)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Intent Accuracy | > 90% | 92.5% | PASS |
| Decision Agreement | > 85% | 88.2% | PASS |
| Knowledge Citation | > 80% | 78.1% | WARN |
| P95 Latency | < 5s | 4.2s | PASS |
| Token Cost/Task | Monitor | 1,234 | - |

### Action Items
- Knowledge citation below target - review knowledge base
- Token cost trending up - optimize prompts
```
