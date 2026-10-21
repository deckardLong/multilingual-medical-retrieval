"""BgeM3Embedder được kiểm tra bằng model GIẢ gắn vào sys.modules (không cần GPU).
Kiểm tra với model thật nằm ở test_real_model.py."""
import sys, types
import numpy as np
import pytest
from retrieval.embedding import validate_encoded


class StubModel:
    dtype = np.float32

    def __init__(self, name, use_fp16=True):
        self.name, self.use_fp16, self.calls, self.fail_above, self.error = name, use_fp16, [], None, None

    def encode(self, texts, batch_size, max_length, return_dense, return_sparse, return_colbert_vecs):
        self.calls.append(dict(n=len(texts), batch_size=batch_size, max_length=max_length, sparse=return_sparse))
        if self.error:
            raise self.error
        if self.fail_above is not None and batch_size > self.fail_above:
            raise RuntimeError("CUDA out of memory")
        d = np.tile(np.eye(1, 1024, dtype=self.dtype), (len(texts), 1))
        out: dict[str, object] = {"dense_vecs": d}
        if return_sparse:
            out["lexical_weights"] = [{"250": 0.5, "7": 0.25} for _ in texts]   # khóa là CHUỖI như FlagEmbedding
        return out


def _install(monkeypatch):
    mod = types.ModuleType("FlagEmbedding"); setattr(mod, "BGEM3FlagModel", StubModel)
    monkeypatch.setitem(sys.modules, "FlagEmbedding", mod)


@pytest.fixture
def embedder(monkeypatch, settings):
    _install(monkeypatch)
    from retrieval.embedding.backends.bge_m3 import BgeM3Embedder
    return BgeM3Embedder(settings.embed)


def test_passes_model_name_and_fp16_to_flagembedding(embedder, settings):
    assert embedder.m.name == settings.embed.model and embedder.m.use_fp16 is settings.embed.fp16
    assert embedder.dim == 1024 and embedder.batch_size == settings.embed.batch_size


def test_converts_lexical_weights_to_sorted_sparse(embedder):
    enc = embedder.encode_docs(["a", "b"])
    assert enc.dense.shape == (2, 1024) and enc.sparse[0].indices == [7, 250]
    assert enc.sparse[0].values == [0.25, 0.5]


def test_output_passes_validation(embedder):
    validate_encoded(embedder.encode_docs(["a", "b", "c"]), 3, 1024, use_sparse=True)


def test_dense_is_always_float32(embedder):
    embedder.m.dtype = np.float16                              # FlagEmbedding với fp16 có thể trả float16
    assert embedder.encode_docs(["a"]).dense.dtype == np.float32


def test_docs_and_queries_use_their_own_max_length(embedder, settings):
    embedder.encode_docs(["a"]); embedder.encode_queries(["a"])
    assert [c["max_length"] for c in embedder.m.calls] == [settings.embed.max_length, settings.embed.query_max_length]


def test_queries_also_get_sparse(embedder):
    assert embedder.encode_queries(["a"]).sparse[0].indices == [7, 250]


def test_empty_input_does_not_call_model(embedder):
    assert embedder.encode_docs([]).dense.shape == (0, 1024) and embedder.m.calls == []
    assert embedder.encode_queries([]).sparse == []


def test_oom_shrinks_batch_and_remembers_it(embedder):
    embedder.m.fail_above = 16
    embedder.encode_docs(["a"])
    assert embedder.batch_size == 16
    embedder.encode_docs(["a"])
    assert embedder.m.calls[-1]["batch_size"] == 16            # không thử lại cỡ đã thất bại


def test_oom_that_never_fits_raises_and_keeps_batch_size(embedder, settings):
    embedder.m.fail_above = 0                                  # batch nào cũng hết VRAM
    with pytest.raises(RuntimeError, match="out of memory"):
        embedder.encode_docs(["a"])
    assert embedder.batch_size == settings.embed.batch_size


def test_non_oom_error_is_not_retried(embedder):
    embedder.m.error = ValueError("input hỏng")
    with pytest.raises(ValueError):
        embedder.encode_docs(["a"])
    assert len(embedder.m.calls) == 1


def test_cuda_cache_is_freed_after_oom(monkeypatch, embedder):
    freed = []
    torch = types.ModuleType("torch")
    setattr(torch, "cuda", types.SimpleNamespace(empty_cache=lambda: freed.append(1)))
    monkeypatch.setitem(sys.modules, "torch", torch)
    embedder.m.fail_above = 16
    embedder.encode_docs(["a"])
    assert len(freed) == 2                                      # 64→32→16: hai lần giảm


def test_missing_torch_does_not_break_oom_recovery(monkeypatch, embedder):
    monkeypatch.setitem(sys.modules, "torch", None)            # import torch → ImportError
    embedder.m.fail_above = 16
    embedder.encode_docs(["a"])
    assert embedder.batch_size == 16


def test_sparse_off_skips_sparse_output(monkeypatch, settings):
    _install(monkeypatch)
    from retrieval.embedding.backends.bge_m3 import BgeM3Embedder
    e = BgeM3Embedder(settings.embed.model_copy(update=dict(use_sparse=False)))
    enc = e.encode_docs(["a", "b"])
    assert [s.indices for s in enc.sparse] == [[], []] and getattr(e.m, "calls")[0]["sparse"] is False