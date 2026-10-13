# Define loader

from pathlib import Path
from typing import TypeVar
import yaml
from .base import Cfg
from .env import Env

C = TypeVar("C", bound=Cfg)

# Read
def _read(p: Path) -> dict:
    return yaml.safe_load(p.read_text("utf-8")) or {}

# Merge
def _merge(base: dict, over: dict) -> dict:
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base

# Load
def load_cfg(name: str, model: type[C], env: Env | None = None) -> C:
    env = env or Env()
    data = _read(env.r2ai_config_dir / f"{name}.yaml")
    if env.r2ai_experiment:
        p = env.r2ai_config_dir / "exp" / env.r2ai_experiment / f"{name}.yaml"
        if p.exists():
            data = _merge(data, _read(p))
    return model.model_validate(data)