"""Mọi backend phải có cùng giao diện (Embedder), để phần còn lại của pipeline không phụ thuộc backend nào."""
import inspect
import pytest
from retrieval.embedding.backends.bge_m3 import BgeM3Embedder
from retrieval.embedding.backends.fake import FakeEmbedder
from retrieval.embedding.base import Embedder


def _params(cls, name):
    return list(inspect.signature(getattr(cls, name)).parameters)


@pytest.mark.parametrize("name", ["encode_docs", "encode_queries"])
@pytest.mark.parametrize("backend", [FakeEmbedder, BgeM3Embedder])
def test_backend_matches_the_embedder_protocol(backend, name):
    assert _params(backend, name) == _params(Embedder, name) == ["self", "texts"]


def test_protocol_declares_dim():
    assert "dim" in Embedder.__annotations__