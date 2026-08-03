from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from loguru import logger

from free_claude_gateway import __version__
from free_claude_gateway.config import Settings, get_settings
from free_claude_gateway.core.balancer import ProviderBalancer
from free_claude_gateway.core.models import AnthropicRequest, ModelInfo
from free_claude_gateway.core.stats import stats
from free_claude_gateway.providers.registry import build_providers, parse_model_ref

app = FastAPI(
    title="Free Claude Gateway",
    version=__version__,
    description="Improved multi-provider proxy for Claude Code and coding agents",
)

_balancer = ProviderBalancer(strategy="priority")


def get_balancer(settings: Settings = Depends(get_settings)) -> ProviderBalancer:
    global _balancer
    if _balancer.strategy != settings.balance_strategy:
        _balancer = ProviderBalancer(strategy=settings.balance_strategy)
    return _balancer


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


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        x in msg
        for x in ("429", "rate limit", "rate_limit", "too many requests", "quota", "resource_exhausted")
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


@app.get("/stats")
async def get_stats(_: None = Depends(verify_auth)):
    """Usage statistics (in-memory, resets on restart)."""
    return stats.get_snapshot()


@app.get("/v1/models")
async def list_models(
    settings: Settings = Depends(get_settings),
    _: None = Depends(verify_auth),
):
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
    balancer: ProviderBalancer = Depends(get_balancer),
    _: None = Depends(verify_auth),
):
    body = await request.json()
    try:
        anth_req = AnthropicRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    target_ref = resolve_model(anth_req.model, settings)
    providers = build_providers(settings)

    base_candidates = [target_ref] + [
        m for m in settings.get_fallback_list() if m != target_ref
    ]

    ordered = balancer.select(
        candidates=base_candidates,
        weights=settings.get_weights() if settings.balance_strategy == "weighted" else None,
    )

    logger.info(f"Strategy={settings.balance_strategy} | order: {ordered}")

    last_error: Exception | None = None

    for ref in ordered:
        provider_name, model_id = parse_model_ref(ref)
        provider = providers.get(provider_name)

        if not provider or not provider.is_available():
            logger.warning(f"Provider {provider_name} not available, skipping")
            continue

        if stats.is_in_cooldown(provider_name):
            logger.warning(f"Provider {provider_name} in cooldown, skipping")
            continue

        try:
            logger.info(f"Routing → {provider_name}/{model_id} (stream={anth_req.stream})")
            if anth_req.stream:
                generator = provider.stream(anth_req, model_id)
                stats.record_success(provider_name)
                return StreamingResponse(
                    generator,
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )
            else:
                result = await provider.chat(anth_req, model_id)
                usage = result.get("usage", {})
                stats.record_success(
                    provider_name,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
                return JSONResponse(content=result)
        except Exception as e:
            is_rl = _is_rate_limit_error(e)
            stats.record_failure(provider_name, str(e), is_rate_limit=is_rl)
            logger.error(f"Provider {provider_name} failed (rate_limit={is_rl}): {e}")
            last_error = e
            continue

    raise HTTPException(
        status_code=502,
        detail=f"All providers failed. Last error: {last_error}",
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(
    settings: Settings = Depends(get_settings),
    _: None = Depends(verify_auth),
):
    """Simple admin / status page."""
    snap = stats.get_snapshot()
    providers = build_providers(settings)

    rows = ""
    for name, p in providers.items():
        available = p.is_available()
        pstats = snap["providers"].get(name, {})
        cooldown = pstats.get("in_cooldown", False)
        status = "Ready" if available and not cooldown else ("Cooldown" if cooldown else "No key")
        rows += f"""
        <tr>
            <td><b>{name}</b></td>
            <td>{status}</td>
            <td>{pstats.get('requests', 0)}</td>
            <td>{pstats.get('successes', 0)}</td>
            <td>{pstats.get('failures', 0)}</td>
            <td>{pstats.get('rate_limits', 0)}</td>
            <td>{pstats.get('input_tokens', 0)} / {pstats.get('output_tokens', 0)}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Free Claude Gateway – Admin</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; background: #0f1115; color: #e1e4e8; }}
    h1 {{ color: #58a6ff; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
    th, td {{ padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid #30363d; }}
    th {{ background: #161b22; color: #8b949e; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.2rem; margin-bottom: 1.5rem; }}
    .muted {{ color: #8b949e; font-size: 0.9rem; }}
    a {{ color: #58a6ff; }}
  </style>
</head>
<body>
  <h1>Free Claude Gateway</h1>
  <p class="muted">v{__version__} · Uptime {snap['uptime_seconds']}s · Total requests: {snap['total_requests']}</p>

  <div class="card">
    <h3>Current Config</h3>
    <p><b>Strategy:</b> {settings.balance_strategy}</p>
    <p><b>Opus:</b> {settings.model_opus}</p>
    <p><b>Sonnet:</b> {settings.model_sonnet}</p>
    <p><b>Haiku:</b> {settings.model_haiku}</p>
    <p><b>Fallback chain:</b> {settings.fallback_chain}</p>
  </div>

  <div class="card">
    <h3>Providers</h3>
    <table>
      <thead>
        <tr>
          <th>Provider</th>
          <th>Status</th>
          <th>Requests</th>
          <th>OK</th>
          <th>Fail</th>
          <th>RateLimit</th>
          <th>Tokens (in/out)</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>

  <p class="muted">
    API: <a href="/stats">/stats</a> · <a href="/health">/health</a> · <a href="/docs">/docs</a>
  </p>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/")
async def root():
    return {
        "name": "Free Claude Gateway",
        "version": __version__,
        "docs": "/docs",
        "admin": "/admin",
        "stats": "/stats",
        "health": "/health",
    }
