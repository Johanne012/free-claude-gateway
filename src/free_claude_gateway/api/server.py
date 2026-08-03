from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from loguru import logger
from sqlalchemy.orm import Session

from free_claude_gateway import __version__
from free_claude_gateway.config import Settings, get_settings
from free_claude_gateway.core.balancer import ProviderBalancer
from free_claude_gateway.core.models import AnthropicRequest, ModelInfo
from free_claude_gateway.core.stats import stats
from free_claude_gateway.db.database import SessionLocal, authenticate_api_key, init_db
from free_claude_gateway.db.models import ApiKey, RequestLog
from free_claude_gateway.providers.registry import build_providers, parse_model_ref

app = FastAPI(
    title="Free Claude Gateway",
    version=__version__,
    description="Real multi-provider AI gateway with users, API keys and usage database",
)

_balancer = ProviderBalancer(strategy="priority")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_balancer(settings: Settings = Depends(get_settings)) -> ProviderBalancer:
    global _balancer
    if _balancer.strategy != settings.balance_strategy:
        _balancer = ProviderBalancer(strategy=settings.balance_strategy)
    return _balancer


def verify_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> Optional[ApiKey]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_key:
        token = x_api_key.strip()

    if not token:
        if not settings.auth_token:
            return None
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = authenticate_api_key(db, token)
    if api_key:
        api_key.last_used_at = datetime.utcnow()
        db.commit()
        return api_key

    if settings.auth_token and token == settings.auth_token:
        return None

    raise HTTPException(status_code=401, detail="Invalid API key")


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
    return any(x in msg for x in ("429", "rate limit", "rate_limit", "too many requests", "quota", "resource_exhausted"))


def _log_request(
    db: Session,
    api_key: Optional[ApiKey],
    provider: str,
    model: str,
    success: bool,
    is_stream: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: float | None = None,
    error: str | None = None,
) -> None:
    log = RequestLog(
        user_id=api_key.user_id if api_key else None,
        api_key_id=api_key.id if api_key else None,
        provider=provider,
        model=model,
        success=success,
        is_stream=is_stream,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        error_message=error[:500] if error else None,
    )
    db.add(log)
    db.commit()


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


@app.get("/stats")
async def get_stats(
    api_key: Optional[ApiKey] = Depends(verify_auth),
    db: Session = Depends(get_db),
):
    mem = stats.get_snapshot()
    total_db = db.query(RequestLog).count()
    success_db = db.query(RequestLog).filter(RequestLog.success == True).count()  # noqa: E712
    return {
        "memory": mem,
        "database": {"total_requests": total_db, "successful_requests": success_db},
    }


@app.get("/v1/models")
async def list_models(
    settings: Settings = Depends(get_settings),
    api_key: Optional[ApiKey] = Depends(verify_auth),
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
    api_key: Optional[ApiKey] = Depends(verify_auth),
    db: Session = Depends(get_db),
):
    body = await request.json()
    try:
        anth_req = AnthropicRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    target_ref = resolve_model(anth_req.model, settings)
    providers = build_providers(settings)
    base_candidates = [target_ref] + [m for m in settings.get_fallback_list() if m != target_ref]
    ordered = balancer.select(
        candidates=base_candidates,
        weights=settings.get_weights() if settings.balance_strategy == "weighted" else None,
    )
    logger.info(f"Strategy={settings.balance_strategy} | order: {ordered}")

    last_error: Exception | None = None
    start_ts = time.time()

    for ref in ordered:
        provider_name, model_id = parse_model_ref(ref)
        provider = providers.get(provider_name)
        if not provider or not provider.is_available():
            continue
        if stats.is_in_cooldown(provider_name):
            continue

        try:
            logger.info(f"Routing → {provider_name}/{model_id} (stream={anth_req.stream})")
            if anth_req.stream:
                generator = provider.stream(anth_req, model_id)
                stats.record_success(provider_name)
                _log_request(db, api_key, provider_name, model_id, True, True, latency_ms=(time.time()-start_ts)*1000)
                return StreamingResponse(generator, media_type="text/event-stream",
                                         headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
            else:
                result = await provider.chat(anth_req, model_id)
                usage = result.get("usage", {})
                stats.record_success(provider_name, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
                _log_request(db, api_key, provider_name, model_id, True, False,
                             usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                             (time.time()-start_ts)*1000)
                return JSONResponse(content=result)
        except Exception as e:
            is_rl = _is_rate_limit_error(e)
            stats.record_failure(provider_name, str(e), is_rate_limit=is_rl)
            _log_request(db, api_key, provider_name, model_id, False, anth_req.stream, error=str(e),
                         latency_ms=(time.time()-start_ts)*1000)
            last_error = e
            continue

    raise HTTPException(status_code=502, detail=f"All providers failed. Last error: {last_error}")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(
    settings: Settings = Depends(get_settings),
    api_key: Optional[ApiKey] = Depends(verify_auth),
    db: Session = Depends(get_db),
):
    snap = stats.get_snapshot()
    providers = build_providers(settings)
    total_logs = db.query(RequestLog).count()
    rows = ""
    for name, p in providers.items():
        available = p.is_available()
        pstats = snap["providers"].get(name, {})
        cooldown = pstats.get("in_cooldown", False)
        status = "Ready" if available and not cooldown else ("Cooldown" if cooldown else "No key")
        rows += f"<tr><td><b>{name}</b></td><td>{status}</td><td>{pstats.get('requests',0)}</td><td>{pstats.get('successes',0)}</td><td>{pstats.get('failures',0)}</td><td>{pstats.get('rate_limits',0)}</td><td>{pstats.get('input_tokens',0)}/{pstats.get('output_tokens',0)}</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Free Claude Gateway</title>
<style>body{{font-family:system-ui;max-width:960px;margin:2rem auto;padding:0 1rem;background:#0f1115;color:#e1e4e8}}
h1{{color:#58a6ff}}table{{width:100%;border-collapse:collapse}}th,td{{padding:.6rem;border-bottom:1px solid #30363d}}
th{{background:#161b22;color:#8b949e}}.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1.2rem;margin-bottom:1.5rem}}
.muted{{color:#8b949e;font-size:.9rem}}</style></head><body>
<h1>Free Claude Gateway</h1>
<p class=\"muted\">v{__version__} · DB requests: {total_logs} · Memory: {snap['total_requests']}</p>
<div class=\"card\"><h3>Config</h3>
<p><b>Strategy:</b> {settings.balance_strategy}</p>
<p><b>Opus:</b> {settings.model_opus}</p>
<p><b>Sonnet:</b> {settings.model_sonnet}</p>
<p><b>Haiku:</b> {settings.model_haiku}</p></div>
<div class=\"card\"><h3>Providers</h3>
<table><thead><tr><th>Provider</th><th>Status</th><th>Req</th><th>OK</th><th>Fail</th><th>RL</th><th>Tokens</th></tr></thead>
<tbody>{rows}</tbody></table></div></body></html>"""
    return HTMLResponse(content=html)


@app.get("/")
async def root():
    return {"name": "Free Claude Gateway", "version": __version__, "docs": "/docs", "admin": "/admin", "stats": "/stats", "health": "/health"}
