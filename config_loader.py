"""
Load configuration from config.yaml with sensible defaults.
"""

from __future__ import annotations

import os
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # Fallback if not installed; callers should handle None


DEFAULT_CONFIG: Dict[str, Any] = {
    "serial": {
        "port": None,
        "baud": 115200,
        "timeout_ms": 1000,
        "retry_interval_s": 5,
    },
    "display": {
        "width": 480,
        "height": 320,
        "fullscreen": False,
        "framerate_hz": 30,
        "screens": ["dashboard", "graph", "settings"],
    },
    "logging": {
        "enabled": True,
        "directory": "./logs",
        "csv_format": True,
        "retention_hours": 24,
        "buffer_size": None,
        "flush_interval_s": 5,
    },
}


def deep_update(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    if not yaml:
        return cfg
    if not os.path.exists(path):
        return cfg
    try:
        with open(path, "r") as f:
            file_cfg = yaml.safe_load(f) or {}
        if isinstance(file_cfg, dict):
            cfg = deep_update(cfg, file_cfg)
    except Exception:
        # Return defaults on error
        return cfg
    return cfg
