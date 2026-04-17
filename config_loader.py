"""
Load configuration from config.yaml with sensible defaults.
"""

from __future__ import annotations

import os
import copy
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # Fallback if not installed; callers should handle None


DEFAULT_CONFIG: Dict[str, Any] = {
    "serial": {
        "port": None,
        "baud": 115200,
    },
    "arduino_temp": {
        "enabled": True,
        "port": "/dev/ttyACM0",
        "baud": 9600,
        "decimals": 2,
        "send_interval_s": 0.5,
    },
    "trigger": {
        "temperature_celsius": None,
        "direction": "below",
        "command": "CHARGE",
        "once": True,
    },
    "logging": {
        "enabled": True,
        "directory": "./logs",
        "retention_hours": 24,
        "flush_interval_s": 1,
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
    cfg = copy.deepcopy(DEFAULT_CONFIG)
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
