from __future__ import annotations

import os
import subprocess
import sys

import uvicorn
from loguru import logger

from free_claude_gateway.config import get_settings


def main() -> None:
    """Start the gateway server."""
    settings = get_settings()
    logger.info(f"Starting Free Claude Gateway on {settings.host}:{settings.port}")
    uvicorn.run(
        "free_claude_gateway.api.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )


def launch_claude() -> None:
    """Launch Claude Code pointed at the local gateway."""
    settings = get_settings()
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = f"http://{settings.host}:{settings.port}"
    env["ANTHROPIC_AUTH_TOKEN"] = settings.auth_token or "fcc"
    env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"

    cmd = ["claude"] + sys.argv[1:]
    logger.info(f"Launching: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, env=env, check=False)
    except FileNotFoundError:
        print("Error: 'claude' command not found. Install Claude Code first.")
        sys.exit(1)
