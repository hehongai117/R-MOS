"""Demo-only API endpoints for investor presentation.

Provides:
- POST /demo/chat/stream — SSE-streamed mock LLM response (no real LLM call)
- POST /demo/fault/start — trigger a gradual fault scenario
- POST /demo/fault/reset — clear all faults

All endpoints are intentionally unauthenticated and bypass the normal
agent / LLM routing stack so demo quality is fully deterministic.
"""
import json
import uuid
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.adapters.factory import AdapterFactory
from app.services.llm.mock_provider import match_intent, stream_text
from app.services.simulation.fault_scenarios import DEMO_SCENARIOS


router = APIRouter(prefix="/demo", tags=["demo"])


class DemoChatRequest(BaseModel):
    message: str
    fault_context: Optional[dict] = None


class DemoFaultRequest(BaseModel):
    scenario: str = "knee_overheat"


@router.post("/chat/stream")
async def demo_chat_stream(body: DemoChatRequest):
    """SSE endpoint that streams mock LLM responses."""
    response = match_intent(body.message)
    trace_id = str(uuid.uuid4())[:8]

    async def event_generator():
        meta = {
            "type": "meta",
            "trace_id": trace_id,
            "diagnosis": response.diagnosis,
            "citations": response.citations,
            "sop_recommendation": response.sop_recommendation,
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        async for chunk in stream_text(response.text):
            payload = {"type": "text", "content": chunk}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/fault/start")
async def start_demo_fault(body: DemoFaultRequest):
    """Trigger a gradual fault scenario for demo."""
    scenario = DEMO_SCENARIOS.get(body.scenario)
    if not scenario:
        return {"error": f"Unknown scenario: {body.scenario}"}

    adapter = await AdapterFactory.get_adapter()
    result = await adapter.start_gradual_fault(
        fault_type=scenario["fault_type"],
        joint_id=scenario["joint_id"],
        ramp_duration=scenario["ramp_duration"],
        target_temp_increase=scenario["target_temp_increase"],
    )
    return result


@router.post("/fault/reset")
async def reset_demo_fault():
    """Reset all faults to normal state."""
    adapter = await AdapterFactory.get_adapter()
    result = await adapter.reset_gradual_faults()
    return result
