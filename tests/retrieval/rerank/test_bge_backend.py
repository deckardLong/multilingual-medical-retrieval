"""BgeRerankerScorer được kiểm tra bằng model GIẢ gắn vào sys.modules (không cần GPU).
Kiểm tra với model thật nằm ở test_real_model.py."""
import sys, types
import numpy as np
import pytest
from factories import cand
from retrieval.rerank import Reranker, RerankError


class StubReranker:
    def __init__(self, name, use_fp16=True):
        self.name, self.use_fp16 = name, use_fp16
        self.calls, self.fail_above, self.error, self.output = [], None, None, None

    def compute_score(self, pairs, batch_size, max_length, normalize):
        self.calls.append(dict(n=len(pairs), bs=batch_size, ml=max_length, norm=normalize, pairs=pairs))
        if self.error:
            raise self.error
        if self.fail_above is not None and batch_size > self.fail_above:
            raise RuntimeError("CUDA out of memory")
        return self.output(pairs) if self.output else [0.25] * len(pairs)


def _install(monkeypatch):
    mod = types.ModuleType("FlagEmbedding"); setattr(mod, "FlagReranker", StubReranker)
    monkeypatch.setitem(sys.modules, "FlagEmbedding", mod)


@pytest.fixture
def scorer(monkeypatch, settings):
    _install(monkeypatch)
    from retrieval.rerank.backends.bge_reranker import BgeRerankerScorer
    return BgeRerankerScorer(settings.rerank)


def test_passes_model_name_and_fp16(scorer, settings):
    assert scorer.m.name == settings.rerank.model and scorer.m.use_fp16 is settings.rerank.fp16
    assert scorer.batch_size == settings.rerank.batch_size


def test_scores_and_params(scorer, settings):
    assert scorer.score_pairs([("q", "a"), ("q", "b")]) == [0.25, 0.25]
    c = scorer.m.calls[0]
    assert c["norm"] is True and c["ml"] == settings.rerank.max_length
    assert c["pairs"] == [["q", "a"], ["q", "b"]]                   # cặp [query, passage], đúng thứ tự


def test_numpy_output_becomes_plain_python_floats(scorer):
    scorer.m.output = lambda pairs: np.linspace(0.1, 0.9, len(pairs), dtype=np.float32)
    out = scorer.score_pairs([("q", "a"), ("q", "b"), ("q", "c")])
    assert len(out) == 3 and all(type(x) is float for x in out)
    assert out == pytest.approx([0.1, 0.5, 0.9], abs=1e-6)


def test_single_pair_scalar_result(scorer):
    scorer.m.compute_score = lambda *a, **k: 0.7          # FlagEmbedding có thể trả float cho 1 cặp
    assert scorer.score_pairs([("q", "a")]) == [0.7]


def test_single_pair_numpy_scalar_result(scorer):
    scorer.m.compute_score = lambda *a, **k: np.float32(0.5)
    assert scorer.score_pairs([("q", "a")]) == [0.5]


def test_empty_skips_model(scorer):
    assert scorer.score_pairs([]) == [] and scorer.m.calls == []


def test_oom_backoff_remembered(scorer):
    scorer.m.fail_above = 8
    scorer.score_pairs([("q", "a")])
    assert scorer.batch_size == 8
    scorer.score_pairs([("q", "a")])
    assert scorer.m.calls[-1]["bs"] == 8


def test_oom_that_never_fits_raises_and_keeps_batch_size(scorer, settings):
    scorer.m.fail_above = 0
    with pytest.raises(RuntimeError, match="out of memory"):
        scorer.score_pairs([("q", "a")])
    assert scorer.batch_size == settings.rerank.batch_size


def test_non_oom_error_is_not_retried(scorer):
    scorer.m.error = ValueError("input hỏng")
    with pytest.raises(ValueError):
        scorer.score_pairs([("q", "a")])
    assert len(scorer.m.calls) == 1


def test_cuda_cache_is_freed_after_oom(monkeypatch, scorer):
    freed = []
    torch = types.ModuleType("torch")
    setattr(torch, "cuda", types.SimpleNamespace(empty_cache=lambda: freed.append(1)))
    monkeypatch.setitem(sys.modules, "torch", torch)
    scorer.m.fail_above = 8                                 # 32→16→8: hai lần giảm
    scorer.score_pairs([("q", "a")])
    assert len(freed) == 2


def test_missing_torch_does_not_break_oom_recovery(monkeypatch, scorer):
    monkeypatch.setitem(sys.modules, "torch", None)
    scorer.m.fail_above = 8
    scorer.score_pairs([("q", "a")])
    assert scorer.batch_size == 8


def test_unnormalized_logits_are_caught_by_the_service(scorer, rcfg):
    """Nếu bản FlagEmbedding bỏ qua normalize=True và trả logit thô (âm hoặc > 1), service phải dừng chứ không lặng lẽ
    xếp hạng/lọc ngưỡng theo điểm sai thang."""
    scorer.m.output = lambda pairs: [-3.2, 5.1][: len(pairs)]
    with pytest.raises(RerankError):
        Reranker(scorer, rcfg).rerank(["q"], [cand(0, "a"), cand(1, "b")])