import numpy as np
import pytest
from common.io import read_vectors, write_chunks
from factories import article
from retrieval.embedding import EmbeddingError, build_embedder, encode_shard
from retrieval.embedding.texts import chunk_texts


@pytest.fixture
def chunks_file(tmp_path, chunker):
    chunks = [c for i in range(3) for c in chunker.split(article(sections=3, paras=3, uid=f"vi:{i + 1}"))]
    p = tmp_path / "chunks.parquet"
    write_chunks(chunks, p)
    return p, chunks


def test_ids_order_and_shapes_match_chunks(tmp_path, chunks_file, fake_cfg):
    path, chunks = chunks_file
    st = encode_shard(path, tmp_path / "v.parquet", build_embedder(fake_cfg), fake_cfg)   # slice_size=8 < n_chunks
    b = read_vectors(tmp_path / "v.parquet")
    assert len(chunks) > fake_cfg.slice_size
    assert b.ids == [c.chunk_id for c in chunks] and st.n_chunks == len(chunks)
    assert b.dense.shape == (len(chunks), fake_cfg.dim) and len(b.sparse) == len(chunks)


def test_row_i_is_the_embedding_of_chunk_i(tmp_path, chunks_file, fake_cfg):
    """Chống lệch hàng giữa các lát: vector hàng i phải là của đúng văn bản (ctx + text) của chunk i."""
    path, chunks = chunks_file
    emb = build_embedder(fake_cfg)
    encode_shard(path, tmp_path / "v.parquet", emb, fake_cfg)
    b = read_vectors(tmp_path / "v.parquet")
    texts = chunk_texts([c.ctx for c in chunks], [c.text for c in chunks])
    for i, t in enumerate(texts):
        one = emb.encode_docs([t])
        assert np.allclose(b.dense[i], one.dense[0], atol=1e-3), f"dense hàng {i}"
        assert b.sparse[i].indices == one.sparse[0].indices, f"sparse hàng {i}"
        assert np.allclose(b.sparse[i].values, one.sparse[0].values, atol=1e-6), f"sparse hàng {i}"


def test_slice_size_does_not_change_the_result(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file
    emb = build_embedder(fake_cfg)
    encode_shard(path, tmp_path / "a.parquet", emb, fake_cfg.model_copy(update=dict(slice_size=2)))
    encode_shard(path, tmp_path / "b.parquet", emb, fake_cfg.model_copy(update=dict(slice_size=1000)))
    a, b = read_vectors(tmp_path / "a.parquet"), read_vectors(tmp_path / "b.parquet")
    assert np.array_equal(a.dense, b.dense) and a.sparse == b.sparse


def test_rerun_is_idempotent(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file
    emb = build_embedder(fake_cfg)
    encode_shard(path, tmp_path / "v1.parquet", emb, fake_cfg)
    encode_shard(path, tmp_path / "v2.parquet", emb, fake_cfg)
    assert (tmp_path / "v1.parquet").read_bytes() == (tmp_path / "v2.parquet").read_bytes()


def test_embeds_ctx_plus_text(tmp_path, chunks_file, fake_cfg):
    path, chunks = chunks_file
    seen = []
    emb = build_embedder(fake_cfg)
    orig = emb.encode_docs
    emb.encode_docs = lambda texts: (seen.extend(texts), orig(texts))[1]
    encode_shard(path, tmp_path / "v.parquet", emb, fake_cfg)
    assert len(seen) == len(chunks)
    assert seen[0].startswith(chunks[0].ctx) and seen[0].endswith(chunks[0].text)


def test_stored_fp16_vectors_are_still_unit_length(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file
    encode_shard(path, tmp_path / "v.parquet", build_embedder(fake_cfg), fake_cfg)
    norms = np.linalg.norm(read_vectors(tmp_path / "v.parquet").dense, axis=1)
    assert np.abs(norms - 1).max() < 0.01


def test_stats_report_throughput_and_mean_sparse_nnz(tmp_path, chunks_file, fake_cfg):
    path, chunks = chunks_file
    st = encode_shard(path, tmp_path / "v.parquet", build_embedder(fake_cfg), fake_cfg)
    b = read_vectors(tmp_path / "v.parquet")
    assert st.mean_sparse_nnz == pytest.approx(sum(len(s.indices) for s in b.sparse) / len(chunks))
    assert st.seconds > 0 and st.chunks_per_s > 0


def test_sparse_off_writes_empty_sparse_without_error(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file
    cfg = fake_cfg.model_copy(update=dict(use_sparse=False))
    st = encode_shard(path, tmp_path / "v.parquet", build_embedder(cfg), cfg)
    b = read_vectors(tmp_path / "v.parquet")
    assert all(not s.indices for s in b.sparse) and st.mean_sparse_nnz == 0


def test_empty_shard_writes_empty_vector_file(tmp_path, fake_cfg):
    write_chunks([], tmp_path / "c.parquet")
    st = encode_shard(tmp_path / "c.parquet", tmp_path / "v.parquet", build_embedder(fake_cfg), fake_cfg)
    b = read_vectors(tmp_path / "v.parquet")
    assert st.n_chunks == 0 and b.ids == [] and b.dense.shape == (0, fake_cfg.dim)
    assert st.mean_sparse_nnz == 0 and st.chunks_per_s == 0


def test_invalid_embeddings_abort_without_writing(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file

    class Bad:
        def encode_docs(self, texts):
            e = build_embedder(fake_cfg).encode_docs(texts); e.dense[0, 0] = np.nan; return e

    with pytest.raises(Exception, match="NaN"):
        encode_shard(path, tmp_path / "v.parquet", Bad(), fake_cfg)
    assert not (tmp_path / "v.parquet").exists() and not list(tmp_path.glob("*.tmp"))


def test_failure_in_a_later_slice_leaves_no_partial_file(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file
    good = build_embedder(fake_cfg)

    class Late:
        n = 0
        def encode_docs(self, texts):
            self.n += 1
            e = good.encode_docs(texts)
            if self.n == 2:
                e.dense[0, 0] = np.inf
            return e

    with pytest.raises(EmbeddingError):
        encode_shard(path, tmp_path / "v.parquet", Late(), fake_cfg)
    assert not (tmp_path / "v.parquet").exists() and not list(tmp_path.glob("*.tmp"))


def test_embedder_returning_too_few_rows_aborts(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file
    good = build_embedder(fake_cfg)

    class Short:
        def encode_docs(self, texts):
            return good.encode_docs(texts[:-1])

    with pytest.raises(EmbeddingError, match="hình"):
        encode_shard(path, tmp_path / "v.parquet", Short(), fake_cfg)
    assert not (tmp_path / "v.parquet").exists()


def test_dim_mismatch_with_config_aborts(tmp_path, chunks_file, fake_cfg):
    path, _ = chunks_file
    wrong = fake_cfg.model_copy(update=dict(dim=32))            # embedder xuất 64 chiều, cấu hình đòi 32
    with pytest.raises(EmbeddingError, match="hình"):
        encode_shard(path, tmp_path / "v.parquet", build_embedder(fake_cfg), wrong)
    assert not (tmp_path / "v.parquet").exists()