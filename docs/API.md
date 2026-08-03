# Free Claude Gateway – API Documentation

**Version:** 0.3.0  
**Base URL (default):** `http://127.0.0.1:8082`

Anthropic Messages API compatible gateway with real users, API keys, budgets and cost tracking.

Interactive docs: `/docs` · ReDoc: `/redoc`

---

## Authentication

| Header | Example |
|--------|--------|
| `Authorization: Bearer <key>` | `Bearer fcc_xxxxxxxxxxxx` |
| `x-api-key: <key>` | `fcc_xxxxxxxxxxxx` |

Keys are stored hashed in SQLite. A default `admin` key is printed on first start.

---

## Endpoints

### Health

```http
GET /health
```
No auth. Returns `{ "status": "ok", "version": "0.3.0" }`.

### List Models

```http
GET /v1/models
```
Auth required. Returns configured Opus/Sonnet/Haiku + fallback models.

### Create Message (core)

```http
POST /v1/messages
```
Auth required. Anthropic-compatible body (`model`, `messages`, `max_tokens`, `stream`, …).

**Budget enforcement:** if the key has exceeded daily/monthly spend, requests or tokens limits → **429**.

**Cost:** each successful request is priced and stored as `cost_usd` in `request_logs`.

### Stats

```http
GET /stats
```
Auth required.

```json
{
  "memory": { "uptime_seconds": 3600, "total_requests": 42, "providers": {} },
  "database": {
    "total_requests": 42,
    "successful_requests": 40,
    "total_cost_usd": 0.0123,
    "total_input_tokens": 15000,
    "total_output_tokens": 8000
  },
  "current_key": {
    "requests_today": 10,
    "tokens_today": 5000,
    "spend_today_usd": 0.004,
    "spend_month_usd": 0.05
  }
}
```

### Admin

```http
GET /admin
```
Auth required. HTML dashboard with config, provider status and total cost.

---

## Budgets (per API key)

| DB column | Meaning |
|-----------|--------|
| `max_spend_per_day_usd` | Daily USD cap (0 = unlimited) |
| `max_spend_per_month_usd` | Monthly USD cap |
| `max_requests_per_day` | Daily request limit |
| `max_tokens_per_day` | Daily token limit |

---

## Errors

| Status | Meaning |
|--------|--------|
| 400 | Invalid body |
| 401 | Missing/invalid key |
| 429 | Budget exceeded |
| 502 | All providers failed |

---

## Claude Code

```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:8082"
export ANTHROPIC_AUTH_TOKEN="fcc_your_real_key"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY="1"
claude
```
