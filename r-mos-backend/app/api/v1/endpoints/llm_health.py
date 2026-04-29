"""
LLM Health Check Endpoint — Task 15
Reports connectivity status of configured LLM providers.
"""
from fastapi import APIRouter

from app.core.config import settings
from app.services.llm.router import LLMRouter, LLMProvider

router = APIRouter(prefix="/llm")


@router.get("/health")
async def llm_health():
    """Check health of all configured LLM providers."""
    llm_router = LLMRouter()
    providers_status = {}

    # Check primary provider
    primary = settings.LLM_PRIMARY_PROVIDER
    providers_status[primary] = await _check_provider(llm_router, primary)

    # Check fallback provider
    fallback = settings.LLM_FALLBACK_PROVIDER
    if fallback and fallback != primary:
        providers_status[fallback] = await _check_provider(llm_router, fallback)

    # Mock is always available
    providers_status["mock"] = {"status": "ok", "message": "Mock provider always available"}

    any_ok = any(p["status"] == "ok" for p in providers_status.values())

    return {
        "overall": "ok" if any_ok else "degraded",
        "providers": providers_status,
        "primary": primary,
        "fallback": fallback,
        "mock_fallback_enabled": settings.LLM_ENABLE_MOCK_FALLBACK,
    }


async def _check_provider(llm_router: LLMRouter, provider_name: str) -> dict:
    """Ping a provider with a minimal request."""
    try:
        provider_enum = LLMProvider(provider_name)
        response = await llm_router.chat(
            messages=[{"role": "user", "content": "ping"}],
            provider=provider_enum.value,
            model="default",
            max_tokens=1,
        )
        return {"status": "ok", "model": response.model}
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}
