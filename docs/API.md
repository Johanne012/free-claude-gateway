# Free Claude Gateway – API Documentation

**Version:** 0.2.0  
**Base URL (default):** `http://127.0.0.1:8082`

The gateway exposes an **Anthropic Messages API compatible** interface so Claude Code and similar clients can use it without modification.

Interactive docs (Swagger): `/docs`  
ReDoc: `/redoc`

---

## Authentication

All protected endpoints accept one of:

| Header | Example |
|--------|---------|
| `Authorization: Bearer <key>` | `Authorization: Bearer fcc_xxxxxxxxxxxx` |
| `x-api-key: <key>` | `x-api-key: fcc_xxxxxxxxxxxx` |

- Real API keys are stored in the database (created on first run for the `admin` user).
- For backward compatibility, the value of `AUTH_TOKEN` from `.env` is still accepted.

---

## Endpoints

### 1. Health Check

```http
GET /health
```

**Auth:** Not required

**Response:**
```json
{
  "status": "ok",
  "version": "0.2.0"
}
```

---

### 2. Root / Info

```http
GET /
```

**Auth:** Not required

---

### 3. List Models

```http
GET /v1/models
```

**Auth:** Required

Returns the models configured for Opus / Sonnet / Haiku tiers plus the fallback chain.  
This endpoint enables Claude Code native `/model` picker.

---

### 4. Create Message (Core Endpoint)

```http
POST /v1/messages
```

**Auth:** Required  
**Content-Type:** `application/json`

Main endpoint used by Claude Code. Compatible with the Anthropic Messages API.

#### Request Body (main fields)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | Model name (e.g. `claude-sonnet-4` or `provider/model`) |
| `messages` | array | Yes | Conversation messages |
| `max_tokens` | integer | No | Default 4096 |
| `stream` | boolean | No | Default false |
| `temperature` | number | No | Sampling temperature |
| `system` | string or array | No | System prompt |
| `tools` | array | No | Tool definitions |

#### Example

```bash
curl -X POST http://127.0.0.1:8082/v1/messages \
  -H "Authorization: Bearer fcc_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

#### Streaming

Set `"stream": true` for Server-Sent Events (Anthropic format).

#### Routing Behavior

1. `model` is mapped to configured provider/model (Opus / Sonnet / Haiku / fallback).
2. Balancer (`BALANCE_STRATEGY`) decides candidate order.
3. Providers in cooldown (after rate-limit) are skipped.
4. On failure the next candidate is tried.

---

### 5. Usage Statistics

```http
GET /stats
```

**Auth:** Required

Returns in-memory counters + persistent database counts.

---

### 6. Admin Dashboard

```http
GET /admin
```

**Auth:** Required  
**Response:** HTML page

---

## Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Invalid request body |
| 401 | Missing or invalid API key |
| 502 | All providers failed |

---

## Using with Claude Code

```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:8082"
export ANTHROPIC_AUTH_TOKEN="fcc_your_real_key"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY="1"
claude
```

Or:

```bash
FCC_API_KEY="fcc_your_real_key" uv run fcc-claude
```

---

## Notes

- All requests are logged in SQLite (`request_logs` table).
- Rate-limited providers get a 60-second cooldown.
- Interactive OpenAPI docs available at `/docs` when the server is running.
