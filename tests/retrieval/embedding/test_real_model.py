"""Kiểm tra với BGE-M3 THẬT. Mặc định bị bỏ qua; chạy trên máy có GPU:
    R2AI_TEST_REAL_MODEL=1 pytest -m gpu tests/retrieval/embedding/test_real_model.py"""
import os
import numpy as np
import pytest

pytestmark = [pytest.mark.gpu,
              pytest.mark.skipif(os.environ.get("R2AI_TEST_REAL_MODEL") != "1", reason="cần model thật + GPU")]

VOCAB = 250_002


@pytest.fixture(scope="module")
def real():
    from common.config import Env
    from retrieval.settings import load_all
    from retrieval.embedding import build_embedder
    cfg = load_all(Env()).embed
    return build_embedder(cfg), cfg


def test_smoke_shapes_validation_and_relevance(real):
    from retrieval.embedding import validate_encoded
    e, cfg = real
    enc = e.encode_docs(["Bệnh tiểu đường type 2 có triệu chứng gì?", "Giải bóng đá quốc gia"])
    validate_encoded(enc, 2, cfg.dim, use_sparse=True)
    q = e.encode_queries(["triệu chứng tiểu đường"]).dense[0]
    assert q @ enc.dense[0] > q @ enc.dense[1]


def test_same_concept_across_vi_en_zh(real):
    """Ý của slide BTC: sỏi thận ↔ kidney stones ↔ 肾结石 phải gần nhau hơn một chủ đề không liên quan."""
    e, _ = real
    vi, en, zh, other = e.encode_docs(["sỏi thận", "kidney stones", "肾结石", "giải bóng đá quốc gia"]).dense
    for a, b in [(vi, en), (vi, zh), (en, zh)]:
        assert a @ b > a @ other and a @ b > b @ other


def test_batch_result_matches_one_by_one(real):
    e, _ = real
    texts = ["triệu chứng sỏi thận", "kidney stones symptoms", "肾结石症状 与治疗"]
    together = e.encode_docs(texts).dense
    for i, t in enumerate(texts):
        one = e.encode_docs([t]).dense[0]
        assert float(one @ together[i]) > 0.99                  # padding/fp16 chỉ gây sai lệch rất nhỏ


def test_sparse_is_wellformed_for_all_three_languages(real):
    e, _ = real
    for sv in e.encode_docs(["triệu chứng sỏi thận", "kidney stones symptoms", "肾结石症状"]).sparse:
        assert sv.indices and sv.indices == sorted(set(sv.indices))
        assert all(0 <= i < VOCAB for i in sv.indices) and all(v > 0 and np.isfinite(v) for v in sv.values)


def test_text_longer_than_max_length_is_truncated_not_rejected(real):
    from retrieval.embedding import validate_encoded
    e, cfg = real
    long_text = "Bệnh tiểu đường type 2 là bệnh mạn tính. " * 400        # vượt xa max_length
    validate_encoded(e.encode_docs([long_text]), 1, cfg.dim, use_sparse=True)