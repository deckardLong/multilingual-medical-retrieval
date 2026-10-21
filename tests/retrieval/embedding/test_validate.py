import numpy as np
import pytest
from common.schema import SparseVec
from retrieval.embedding import Encoded, EmbeddingError, validate_encoded


def good(n=6, dim=8):
    d = np.eye(n, dim, dtype=np.float32)
    return Encoded(d, [SparseVec([1, 2], [0.5, 0.2]) for _ in range(n)])


def test_valid_batch_passes():
    validate_encoded(good(), 6, 8, use_sparse=True)


@pytest.mark.parametrize("mutate,msg", [
    (lambda e: setattr(e, "dense", e.dense[:, :4]), "hình"),
    (lambda e: setattr(e, "dense", e.dense[:3]), "hình"),
    (lambda e: e.dense.__setitem__((0, 0), np.nan), "NaN"),
    (lambda e: e.dense.__setitem__((0, 0), np.inf), "NaN"),
    (lambda e: e.dense.__imul__(2), "chuẩn hóa"),
    (lambda e: e.dense.__setitem__((2, slice(None)), 0.0), "chuẩn hóa"),           # một dòng toàn 0
    (lambda e: e.sparse.pop(), "sparse có"),
    (lambda e: e.sparse.__setitem__(0, SparseVec([1, 2], [0.5])), "lệch độ dài"),
    (lambda e: e.sparse.__setitem__(0, SparseVec([3, 3], [0.1, 0.2])), "trùng"),
    (lambda e: e.sparse.__setitem__(0, SparseVec([-1], [0.5])), "âm"),
    (lambda e: e.sparse.__setitem__(0, SparseVec([1], [-0.1])), "values"),
    (lambda e: e.sparse.__setitem__(0, SparseVec([1], [0.0])), "values"),
    (lambda e: e.sparse.__setitem__(0, SparseVec([1], [float("inf")])), "values"),
    (lambda e: e.sparse.__setitem__(0, SparseVec([1], [float("nan")])), "values"),
])
def test_rejects_bad_batches(mutate, msg):
    e = good()
    mutate(e)
    with pytest.raises(EmbeddingError, match=msg):
        validate_encoded(e, 6, 8, use_sparse=True)


def test_error_message_names_the_offending_row():
    e = good()
    e.sparse[4] = SparseVec([1], [-1.0])
    with pytest.raises(EmbeddingError, match=r"sparse\[4\]"):
        validate_encoded(e, 6, 8, use_sparse=True)


def test_all_empty_sparse_is_an_error_only_when_sparse_expected():
    e = Encoded(np.eye(6, 8, dtype=np.float32), [SparseVec([], []) for _ in range(6)])
    validate_encoded(e, 6, 8, use_sparse=False)
    with pytest.raises(EmbeddingError):
        validate_encoded(e, 6, 8, use_sparse=True)


def test_small_batches_may_have_empty_sparse():
    """Dưới 5 phần tử thì 'toàn rỗng' chưa đủ căn cứ để kết luận hỏng."""
    e = Encoded(np.eye(4, 8, dtype=np.float32), [SparseVec([], []) for _ in range(4)])
    validate_encoded(e, 4, 8, use_sparse=True)


def test_a_single_empty_sparse_among_many_is_fine():
    e = good()
    e.sparse[2] = SparseVec([], [])
    validate_encoded(e, 6, 8, use_sparse=True)


def test_empty_batch_is_valid():
    validate_encoded(Encoded(np.zeros((0, 8), np.float32), []), 0, 8, use_sparse=True)


def test_norm_tolerance_boundary():
    e = good()
    e.dense *= 1.01                                    # trong ngưỡng 0.02
    validate_encoded(e, 6, 8, use_sparse=True)
    e.dense *= 1.05                                    # ≈ 1.06, vượt ngưỡng
    with pytest.raises(EmbeddingError, match="chuẩn hóa"):
        validate_encoded(e, 6, 8, use_sparse=True)


def test_fp16_rounding_stays_within_tolerance():
    """encode_shard kiểm tra ở float32 rồi ghi fp16: làm tròn fp16 không được làm vector ra khỏi ngưỡng."""
    rng = np.random.default_rng(0)
    d = rng.normal(size=(50, 1024)).astype(np.float32)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    e = Encoded(d.astype(np.float16).astype(np.float32), [SparseVec([1], [0.5]) for _ in range(50)])
    validate_encoded(e, 50, 1024, use_sparse=True)