# Register & Build chunker

from typing import Callable

# REG
_REG: dict[str, Callable] = {}

# Register
def register(name: str):
    def deco(cls):
        _REG[name] = cls
        return cls
    return deco

# Build chunker
def build_chunker(cfg, counter, tag: str):
    from . import structure, recursive
    return _REG[cfg.method](cfg, counter, tag) 