import sys, types
from types import SimpleNamespace
import pytest
from retrieval.embedding import build_embedder
from retrieval.embedding.backends.fake import FakeEmbedder


def test_fake_backend(fake_cfg):
    assert isinstance(build_embedder(fake_cfg), FakeEmbedder)


def test_unknown_backend_is_rejected(fake_cfg):
    with pytest.raises(ValueError):
        build_embedder(fake_cfg.model_copy(update=dict(backend="qwen3")))


def test_bge_m3_backend_gets_model_name_and_fp16(monkeypatch, settings):
    mod = types.ModuleType("FlagEmbedding")
    setattr(mod, "BGEM3FlagModel", lambda name, use_fp16: SimpleNamespace(name=name, use_fp16=use_fp16))
    monkeypatch.setitem(sys.modules, "FlagEmbedding", mod)
    from retrieval.embedding.backends.bge_m3 import BgeM3Embedder
    e = build_embedder(settings.embed)                      # configs/embed.yaml: backend=bge_m3
    assert isinstance(e, BgeM3Embedder)
    assert getattr(e.m, "name", None) == "BAAI/bge-m3"
    assert getattr(e.m, "use_fp16", None) is True


def test_fake_backend_does_not_need_flagembedding(monkeypatch, fake_cfg):
    monkeypatch.setitem(sys.modules, "FlagEmbedding", None)  # import sẽ báo ImportError
    assert isinstance(build_embedder(fake_cfg), FakeEmbedder)