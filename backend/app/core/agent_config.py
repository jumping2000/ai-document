"""Load agent configuration from YAML files with graceful degradation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "agents"


@lru_cache(maxsize=10)
def load_agent_config(agent_name: str) -> dict:
    """
    Load agent configuration from app/config/agents/{agent_name}.yaml.

    Returns an empty dict if the file doesn't exist — callers must
    fall back to their hard-coded defaults.
    """
    config_path = CONFIG_DIR / f"{agent_name}.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)
