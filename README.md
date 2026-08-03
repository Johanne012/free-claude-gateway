# Free Claude Gateway

**An improved, cleaner multi-provider proxy for Claude Code, Codex, and similar coding agents.**

Route Claude Code (and compatible clients) to free or low-cost providers like DeepSeek, Kimi, NVIDIA NIM, OpenRouter, Ollama, LM Studio, and more — while keeping the original agent experience.

> Inspired by [free-claude-code](https://github.com/Alishahryar1/free-claude-code), rebuilt with a simpler architecture, better defaults for free tiers, automatic fallbacks, and Docker-first design.

## Why this project?

- **Cleaner & more maintainable** — smaller codebase, clear separation of concerns
- **Smart routing & fallbacks** — automatic provider fallback when rate-limited or failing
- **Free-tier focused** — optimized defaults for NVIDIA NIM, OpenRouter free models, DeepSeek, Kimi, and local models
- **Docker ready** — one command to run
- **Simple config** — environment variables
- **Native model picker support** — exposes `/v1/models`
- **Streaming + tool use** preserved

## Quick Start

### Option 1: Docker (recommended)

```bash
git clone https://github.com/Johanne012/free-claude-gateway.git
cd free-claude-gateway
cp .env.example .env
# Edit .env and add at least one provider key
docker compose up -d
```

Health: `http://localhost:8082/health`

### Option 2: Local with uv

```bash
# Install uv if needed: curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/Johanne012/free-claude-gateway.git
cd free-claude-gateway
cp .env.example .env
# Edit .env
uv sync
uv run fcc-gateway
```

### Connect Claude Code

```bash
export ANTHROPIC_BASE_URL="http://localhost:8082"
export ANTHROPIC_AUTH_TOKEN="fcc"
claude
```

Or use the helper:

```bash
uv run fcc-claude
```

## Supported Providers (initial)

| Provider          | Free tier / Notes                          | Env var                  |
|-------------------|--------------------------------------------|--------------------------|
| NVIDIA NIM        | Generous free tier                         | `NVIDIA_NIM_API_KEY`     |
| OpenRouter        | Many free models                           | `OPENROUTER_API_KEY`     |
| DeepSeek          | Very cheap                                 | `DEEPSEEK_API_KEY`       |
| Kimi (Moonshot)   | Strong coding models                       | `KIMI_API_KEY`           |
| Ollama            | Fully local                                | (no key)                 |
| LM Studio         | Fully local                                | (no key)                 |
| Groq              | Fast free tier                             | `GROQ_API_KEY`           |

## Configuration

Copy `.env.example` to `.env` and fill in the keys you have.

You can set different models per Claude tier (Opus / Sonnet / Haiku) and a fallback chain.

## License

MIT
