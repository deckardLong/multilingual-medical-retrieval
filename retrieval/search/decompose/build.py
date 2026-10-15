from .identity import IdentityDecomposer
from .rule import RuleDecomposer

def build_decomposer(cfg):
    if cfg.mode == "off":
        return IdentityDecomposer()
    if cfg.mode == "rule":
        return RuleDecomposer(cfg)
    raise ValueError(f"decompose.mode không hỗ trợ: {cfg.mode}")