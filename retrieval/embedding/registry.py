# Begin to build embedder

def build_embedder(cfg):
    if cfg.backend == "fake":
        from .backends.fake import FakeEmbedder
        return FakeEmbedder(cfg)
    if cfg.backend == "bge_m3":
        from .backends.bge_m3 import BgeM3Embedder
        return BgeM3Embedder(cfg)
    raise ValueError(f"backend không hỗ trợ: {cfg.backend}")