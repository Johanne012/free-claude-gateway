# Contributing to Free Claude Gateway

Thank you for your interest in contributing!

## Development setup

```bash
git clone https://github.com/Johanne012/free-claude-gateway.git
cd free-claude-gateway
cp .env.example .env
uv sync --extra dev
```

## Running the server

```bash
uv run fcc-gateway
```

## Running tests

```bash
uv run pytest
uv run ruff check src tests
```

## Code style

- Python ≥ 3.11
- Line length: 100 (ruff)
- Prefer type hints
- Keep changes focused and well-tested

## Pull requests

1. Create a branch from `main`
2. Make your changes + add tests when relevant
3. Ensure `ruff` and `pytest` pass
4. Open a PR with a clear description

## Ideas for contribution

- Additional providers
- Better tool-use / function-calling support
- Improved admin UI
- PostgreSQL support
- More comprehensive test coverage
