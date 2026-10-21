import numpy as np
from retrieval.embedding import build_embedder, validate_encoded
from retrieval.embedding.backends.fake import VOCAB


def test_deterministic_and_valid(fake_cfg):
    e = build_embedder(fake_cfg)
    a, b = e.encode_docs(["bệnh tiểu đường type 2"]), e.encode_docs(["bệnh tiểu đường type 2"])
    assert np.array_equal(a.dense, b.dense) and a.sparse == b.sparse
    validate_encoded(a, 1, fake_cfg.dim, use_sparse=True)


def test_shared_words_mean_higher_cosine(fake_cfg):
    e = build_embedder(fake_cfg)
    q = e.encode_queries(["triệu chứng tiểu đường"]).dense[0]
    near = e.encode_docs(["các triệu chứng của bệnh tiểu đường"]).dense[0]
    far = e.encode_docs(["giải bóng đá quốc gia mùa này"]).dense[0]
    assert q @ near > q @ far


def test_batch_result_equals_one_by_one(fake_cfg):
    e = build_embedder(fake_cfg)
    texts = ["sỏi thận", "kidney stones symptoms", "", "肾结石症状 治疗"]
    together = e.encode_docs(texts)
    for i, t in enumerate(texts):
        one = e.encode_docs([t])
        assert np.array_equal(together.dense[i], one.dense[0]) and together.sparse[i] == one.sparse[0]


def test_empty_text_still_gives_unit_vector(fake_cfg):
    enc = build_embedder(fake_cfg).encode_docs([""])
    validate_encoded(enc, 1, fake_cfg.dim, use_sparse=False)


def test_case_and_punctuation_do_not_matter(fake_cfg):
    e = build_embedder(fake_cfg)
    assert np.array_equal(e.encode_docs(["Tiểu Đường!"]).dense, e.encode_docs(["tiểu đường"]).dense)


def test_chinese_text_is_embedded(fake_cfg):
    enc = build_embedder(fake_cfg).encode_docs(["糖尿病的症状 糖尿病 治疗"])
    validate_encoded(enc, 1, fake_cfg.dim, use_sparse=True)
    assert enc.sparse[0].indices


def test_sparse_is_sorted_unique_positive_and_in_vocab(fake_cfg):
    sv = build_embedder(fake_cfg).encode_docs(["a b c a b a d e f g"]).sparse[0]
    assert sv.indices == sorted(set(sv.indices)) and all(0 <= i < VOCAB for i in sv.indices)
    assert all(0 < v <= 1.0 for v in sv.values) and max(sv.values) == 1.0     # từ nhiều nhất có trọng số 1


def test_queries_are_truncated_to_query_max_length(fake_cfg):
    e = build_embedder(fake_cfg)                       # query_max_length=16
    long_q = " ".join(f"từ{i}" for i in range(100))
    short_q = " ".join(f"từ{i}" for i in range(fake_cfg.query_max_length))
    assert np.array_equal(e.encode_queries([long_q]).dense, e.encode_queries([short_q]).dense)


def test_docs_are_truncated_to_max_length_but_longer_than_queries(fake_cfg):
    e = build_embedder(fake_cfg)                       # max_length=64, query_max_length=16
    text = " ".join(f"từ{i}" for i in range(200))
    head = " ".join(f"từ{i}" for i in range(fake_cfg.max_length))
    assert np.array_equal(e.encode_docs([text]).dense, e.encode_docs([head]).dense)
    assert not np.array_equal(e.encode_docs([text]).dense, e.encode_queries([text]).dense)


def test_sparse_disabled_gives_empty_vectors(fake_cfg):
    cfg = fake_cfg.model_copy(update=dict(use_sparse=False))
    assert all(not s.indices for s in build_embedder(cfg).encode_docs(["a b c"]).sparse)


def test_empty_batch(fake_cfg):
    enc = build_embedder(fake_cfg).encode_docs([])
    assert enc.dense.shape == (0, fake_cfg.dim) and enc.sparse == []