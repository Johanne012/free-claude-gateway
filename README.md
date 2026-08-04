# Free Claude Gateway

[![CI](https://github.com/Johanne012/free-claude-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/Johanne012/free-claude-gateway/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Real multi-provider AI gateway for Claude Code** with users, API keys, budgets, cost tracking, smart balancing and automatic fallbacks.

Route Claude Code (and compatible clients) to free or low-cost providers like DeepSeek, Kimi, NVIDIA NIM, OpenRouter, Ollama, LM Studio, and more — while keeping the original agent experience.

> Inspired by [free-claude-code](https://github.com/Alishahryar1/free-claude-code), rebuilt cleaner with a real database foundation.

**Version:** 0.4.0  
**API Documentation:** [docs/API.md](docs/API.md)  
**Interactive docs (when running):** http://localhost:8082/docs

## Why this project?

- **Real database** — SQLite with users, API keys and request logs
- **Budgets & cost tracking** — per-key daily/monthly spend limits + real USD cost per request
- **Smart routing & fallbacks** — priority / round-robin / random / weighted + rate-limit cooldown
- **Free-tier focused** — DeepSeek, Kimi, NVIDIA NIM, OpenRouter free models, local models
- **Native model picker** — exposes `/v1/models`
- **Streaming + tool use** preserved
- **Admin dashboard** + usage & cost stats

## Quick Start

```bash
git clone https://github.com/Johanne012/free-claude-gateway.git
cd free-claude-gateway
cp .env.example .env
# Edit .env and add at least one provider key (OPENROUTER_API_KEY, DEEPSEEK_API_KEY, ...)

uv sync
uv run fcc-gateway
```

On first start the server creates an `admin` user and prints a real API key (`fcc_...`). **Save it.**

### Connect Claude Code

```bash
export ANTHROPIC_BASE_URL="http://localhost:8082"
export ANTHROPIC_AUTH_TOKEN="fcc_your_real_key"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY="1"
claude
```

Or use the helper:

```bash
export FCC_API_KEY="fcc_your_real_key"
uv run fcc-claude
```

## Main Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/v1/models` | List available models |
| POST | `/v1/messages` | Anthropic-compatible chat (core) |
| GET | `/stats` | Usage + cost statistics |
| GET | `/admin` | Admin dashboard (includes total cost) |
| GET | `/docs` | Interactive OpenAPI docs |

Full details: **[docs/API.md](docs/API.md)**

## Budgets & Cost Tracking

Every successful request is priced using a built-in model price table and stored as `cost_usd`.

Per API key you can set (in the database / admin UI):

| Field | Meaning |
|-------|--------|
| `max_spend_per_day_usd` | Daily spend cap in USD (0 = unlimited) |
| `max_spend_per_month_usd` | Monthly spend cap |
| `max_requests_per_day` | Daily request limit |
| `max_tokens_per_day` | Daily token limit |

When a limit is hit, the gateway returns **HTTP 429** with a clear message.

`/stats` returns total cost, token counts, and the current key's daily/monthly usage.

## Supported Providers

| Provider | Env var |
|----------|--------|
| NVIDIA NIM | `NVIDIA_NIM_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Kimi | `KIMI_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Ollama / LM Studio | (local, no key) |

## Configuration

See `.env.example` for:

- Per-tier models (`MODEL_OPUS`, `MODEL_SONNET`, `MODEL_HAIKU`)
- Balancing strategy (`priority` / `round_robin` / `random` / `weighted`)
- Fallback chain

## Docker

```bash
cp .env.example .env
# fill keys
docker compose up --build
```

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

MIT
