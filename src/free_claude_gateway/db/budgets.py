"""Budget checks and spend aggregation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from free_claude_gateway.db.models import ApiKey, RequestLog


def _day_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_key_usage(session: Session, api_key_id: int) -> dict:
    day = _day_start()
    month = _month_start()

    day_q = session.execute(
        select(
            func.count(RequestLog.id),
            func.coalesce(func.sum(RequestLog.input_tokens + RequestLog.output_tokens), 0),
            func.coalesce(func.sum(RequestLog.cost_usd), 0.0),
        ).where(
            RequestLog.api_key_id == api_key_id,
            RequestLog.created_at >= day,
            RequestLog.success == True,  # noqa: E712
        )
    ).one()

    month_q = session.execute(
        select(
            func.coalesce(func.sum(RequestLog.cost_usd), 0.0),
        ).where(
            RequestLog.api_key_id == api_key_id,
            RequestLog.created_at >= month,
            RequestLog.success == True,  # noqa: E712
        )
    ).one()

    return {
        "requests_today": int(day_q[0] or 0),
        "tokens_today": int(day_q[1] or 0),
        "spend_today_usd": float(day_q[2] or 0.0),
        "spend_month_usd": float(month_q[0] or 0.0),
    }


def check_budget(session: Session, api_key: Optional[ApiKey]) -> Optional[str]:
    if api_key is None:
        return None

    usage = get_key_usage(session, api_key.id)

    if api_key.max_requests_per_day and usage["requests_today"] >= api_key.max_requests_per_day:
        return f"Daily request limit reached ({api_key.max_requests_per_day})"

    if api_key.max_tokens_per_day and usage["tokens_today"] >= api_key.max_tokens_per_day:
        return f"Daily token limit reached ({api_key.max_tokens_per_day})"

    if api_key.max_spend_per_day_usd and usage["spend_today_usd"] >= api_key.max_spend_per_day_usd:
        return f"Daily spend limit reached (${api_key.max_spend_per_day_usd:.4f})"

    if api_key.max_spend_per_month_usd and usage["spend_month_usd"] >= api_key.max_spend_per_month_usd:
        return f"Monthly spend limit reached (${api_key.max_spend_per_month_usd:.4f})"

    return None
