# Free Claude Gateway

**Real multi-provider AI gateway for Claude Code** with users, API keys, usage database, smart balancing and automatic fallbacks.

Route Claude Code (and compatible clients) to free or low-cost providers like DeepSeek, Kimi, NVIDIA NIM, OpenRouter, Ollama, LM Studio, and more — while keeping the original agent experience.

> Inspired by [free-claude-code](https://github.com/Alishahryar1/free-claude-code), rebuilt cleaner with a real database foundation.

**API Documentation:** [docs/API.md](docs/API.md)  
**Interactive docs (when running):** http://localhost:8082/docs

## Why this project?

- **Real database** — SQLite with users, API keys and request logs
- **Smart routing & fallbacks** — priority / round-robin / random / weighted + rate-limit cooldown
- **Free-tier focused** — DeepSeek, Kimi, NVIDIA NIM, OpenRouter free models, local models
- **Native model picker** — exposes `/v1/models`
- **Streaming + tool use** preserved
- **Admin dashboard** + usage stats

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

## Main Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/v1/models` | List available models |
| POST | `/v1/messages` | Anthropic-compatible chat (core) |
| GET | `/stats` | Usage statistics |
| GET | `/admin` | Simple admin dashboard |
| GET | `/docs` | Interactive OpenAPI docs |

Full details: **[docs/API.md](docs/API.md)**

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

## License

MIT
