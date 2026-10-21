"""Mọi backend/service phải có cùng giao diện, để Retriever không phụ thuộc loại nào được dùng."""
import inspect
import pytest
from retrieval.rerank import NoopReranker, Reranker
from retrieval.rerank.backends.bge_reranker import BgeRerankerScorer
from retrieval.rerank.backends.fake import FakePairScorer
from retrieval.rerank.base import PairScorer


def _params(cls, name):
    return list(inspect.signature(getattr(cls, name)).parameters)


@pytest.mark.parametrize("backend", [FakePairScorer, BgeRerankerScorer])
def test_scorers_match_the_pairscorer_protocol(backend):
    assert _params(backend, "score_pairs") == _params(PairScorer, "score_pairs") == ["self", "pairs"]


def test_reranker_and_noop_are_interchangeable():
    assert _params(Reranker, "rerank") == _params(NoopReranker, "rerank") == ["self", "queries", "cands"]