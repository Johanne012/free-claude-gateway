from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from free_claude_gateway import __version__
from free_claude_gateway.config import Settings, get_settings
from free_claude_gateway.core.models import AnthropicRequest, ModelInfo
from free_claude_gateway.providers.registry import build_providers, parse_model_ref

app = FastAPI(
    title="Free Claude Gateway",
    version=__version__,
    description="Improved multi-provider proxy for Claude Code and coding agents",
)


def verify_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.auth_token:
        return
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_key:
        token = x_api_key.strip()
    if token != settings.auth_token:
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")


def resolve_model(requested: str, settings: Settings) -> str:
    """Map Claude-style model names to configured provider/model."""
    lower = requested.lower()
    if "opus" in lower or "fable" in lower:
        return settings.model_opus
    if "sonnet" in lower:
        return settings.model_sonnet
    if "haiku" in lower:
        return settings.model_haiku
    if "/" in requested:
        return requested
    return settings.model_fallback


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


@app.get("/v1/models")
async def list_models(
    settings: Settings = Depends(get_settings),
    _: None = Depends(verify_auth),
):
    """Expose models so Claude Code native /model picker works."""
    models = [
        ModelInfo(id=settings.model_opus),
        ModelInfo(id=settings.model_sonnet),
        ModelInfo(id=settings.model_haiku),
        ModelInfo(id=settings.model_fallback),
    ]
    for m in settings.get_fallback_list():
        if m not in [x.id for x in models]:
            models.append(ModelInfo(id=m))
    return {"object": "list", "data": [m.model_dump() for m in models]}


@app.post("/v1/messages")
async def create_message(
    request: Request,
    settings: Settings = Depends(get_settings),
    _: None = Depends(verify_auth),
):
    body = await request.json()
    try:
        anth_req = AnthropicRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    target_ref = resolve_model(anth_req.model, settings)
    providers = build_providers(settings)

    candidates = [target_ref] + [m for m in settings.get_fallback_list() if m != target_ref]

    last_error: Exception | None = None

    for ref in candidates:
        provider_name, model_id = parse_model_ref(ref)
        provider = providers.get(provider_name)
        if not provider or not provider.is_available():
            logger.warning(f"Provider {provider_name} not available, skipping")
            continue

        try:
            logger.info(f"Routing → {provider_name}/{model_id} (stream={anth_req.stream})")
            if anth_req.stream:
                generator = provider.stream(anth_req, model_id)
                return StreamingResponse(
                    generator,
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )
            else:
                result = await provider.chat(anth_req, model_id)
                return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Provider {provider_name} failed: {e}")
            last_error = e
            continue

    raise HTTPException(
        status_code=502,
        detail=f"All providers failed. Last error: {last_error}",
    )


@app.get("/")
async def root():
    return {
        "name": "Free Claude Gateway",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
