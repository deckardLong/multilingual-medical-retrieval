"""Gián đoạn giữa chừng một shard (Ctrl-C, mất điện, hết VRAM) thì lần chạy sau phải đi tiếp từ chỗ dở,
và cho ra kết quả giống hệt như chạy một mạch."""
import numpy as np
import pytest
from common.io import read_vectors, write_chunks
from factories import article
from retrieval.embedding import build_embedder, encode_shard
from retrieval.embedding.checkpoint import open_checkpoint, parts_dir


class Flaky:
    """Embedder bọc ngoài: mã hoá bình thường nhưng nổ ở lát thứ `fail_at` (đếm từ 1); đếm số lát đã mã hoá."""

    def __init__(self, inner, fail_at=None):
        self.inner, self.fail_at, self.calls, self.n_texts = inner, fail_at, 0, 0

    def encode_docs(self, texts):
        self.calls += 1
        if self.fail_at is not None and self.calls == self.fail_at:
            raise RuntimeError("CUDA out of memory")
        self.n_texts += len(texts)
        return self.inner.encode_docs(texts)

    def encode_queries(self, texts):
        return self.inner.encode_queries(texts)


@pytest.fixture
def shard(tmp_path, chunker, fake_cfg):
    """24 chunk với slice_size=8 → 3 lát, đủ để 'nổ ở lát thứ 3' có nghĩa."""
    chunks = [c for i in range(6) for c in chunker.split(article(sections=3, paras=3, uid=f"vi:{i + 1}"))]
    assert len(chunks) == 3 * fake_cfg.slice_size
    p = tmp_path / "chunks.parquet"
    write_chunks(chunks, p)
    return p, chunks


def encode(shard_path, out, cfg, emb, **kw):
    return encode_shard(shard_path, out, emb, cfg, **kw)


def test_crash_midway_leaves_the_finished_slices_and_no_vector_file(tmp_path, shard, fake_cfg):
    path, chunks = shard
    out = tmp_path / "v.parquet"
    emb = Flaky(build_embedder(fake_cfg), fail_at=3)
    with pytest.raises(RuntimeError, match="out of memory"):
        encode(path, out, fake_cfg, emb)
    assert not out.exists()                                     # shard chưa xong thì chưa có file vector
    ck = open_checkpoint(out, "bỏ qua fp", len(chunks))         # fp khác → nếu KHÔNG có part thật thì done = 0
    assert ck.done == 0 and parts_dir(out).exists()


def test_rerun_after_a_crash_only_encodes_what_was_left(tmp_path, shard, fake_cfg):
    path, chunks = shard
    out = tmp_path / "v.parquet"
    crashed = Flaky(build_embedder(fake_cfg), fail_at=3)
    with pytest.raises(RuntimeError):
        encode(path, out, fake_cfg, crashed)
    done_before = crashed.n_texts                                # 2 lát đầu đã xong
    assert done_before == 2 * fake_cfg.slice_size

    resumed = Flaky(build_embedder(fake_cfg))
    st = encode(path, out, fake_cfg, resumed)
    assert resumed.n_texts == len(chunks) - done_before          # không mã hoá lại phần đã xong
    assert st.n_chunks == len(chunks) and out.exists()


def test_the_resumed_file_is_identical_to_one_written_in_a_single_run(tmp_path, shard, fake_cfg):
    path, chunks = shard
    straight, resumed_path = tmp_path / "straight.parquet", tmp_path / "resumed.parquet"
    encode(path, straight, fake_cfg, build_embedder(fake_cfg))

    with pytest.raises(RuntimeError):
        encode(path, resumed_path, fake_cfg, Flaky(build_embedder(fake_cfg), fail_at=2))
    encode(path, resumed_path, fake_cfg, build_embedder(fake_cfg))

    a, b = read_vectors(straight), read_vectors(resumed_path)
    assert a.ids == b.ids == [c.chunk_id for c in chunks]
    assert np.array_equal(a.dense, b.dense)
    assert [s.indices for s in a.sparse] == [s.indices for s in b.sparse]
    assert all(np.allclose(x.values, y.values) for x, y in zip(a.sparse, b.sparse))


def test_several_crashes_in_a_row_still_converge(tmp_path, shard, fake_cfg):
    path, chunks = shard
    out = tmp_path / "v.parquet"
    for _ in range(3):
        with pytest.raises(RuntimeError):
            encode(path, out, fake_cfg, Flaky(build_embedder(fake_cfg), fail_at=1))   # nổ ngay lát đầu mỗi lần
    encode(path, out, fake_cfg, build_embedder(fake_cfg))
    assert read_vectors(out).ids == [c.chunk_id for c in chunks]


def test_the_parts_dir_is_cleaned_up_once_the_shard_is_done(tmp_path, shard, fake_cfg):
    path, _ = shard
    out = tmp_path / "v.parquet"
    encode(path, out, fake_cfg, build_embedder(fake_cfg))
    assert not parts_dir(out).exists()


def test_resume_false_forces_the_whole_shard_to_be_encoded_again(tmp_path, shard, fake_cfg):
    path, chunks = shard
    out = tmp_path / "v.parquet"
    with pytest.raises(RuntimeError):
        encode(path, out, fake_cfg, Flaky(build_embedder(fake_cfg), fail_at=3))
    fresh = Flaky(build_embedder(fake_cfg))
    encode(path, out, fake_cfg, fresh, resume=False)
    assert fresh.n_texts == len(chunks)                          # mã hoá lại tất cả, không dùng part cũ
    assert read_vectors(out).ids == [c.chunk_id for c in chunks]


def test_progress_counts_the_resumed_part_too(tmp_path, shard, fake_cfg):
    """Thanh phải nhảy ngay đến phần đã làm từ lần trước, nếu không nó sẽ không bao giờ đầy."""
    path, chunks = shard
    out = tmp_path / "v.parquet"
    with pytest.raises(RuntimeError):
        encode(path, out, fake_cfg, Flaky(build_embedder(fake_cfg), fail_at=3))

    seen = []
    encode(path, out, fake_cfg, build_embedder(fake_cfg), on_progress=seen.append)
    assert sum(seen) == len(chunks) and seen[0] == 2 * fake_cfg.slice_size


def test_progress_is_reported_slice_by_slice_in_a_normal_run(tmp_path, shard, fake_cfg):
    path, chunks = shard
    seen = []
    encode(path, tmp_path / "v.parquet", fake_cfg, build_embedder(fake_cfg), on_progress=seen.append)
    assert sum(seen) == len(chunks) and len(seen) > 1 and max(seen) <= fake_cfg.slice_size


def test_an_empty_shard_finishes_without_a_parts_dir(tmp_path, fake_cfg):
    path = tmp_path / "empty.parquet"
    write_chunks([], path)
    out = tmp_path / "v.parquet"
    st = encode(path, out, fake_cfg, build_embedder(fake_cfg))
    assert st.n_chunks == 0 and read_vectors(out).ids == [] and not parts_dir(out).exists()


class Noisy:
    """Mô phỏng FlagEmbedding: tự vẽ thanh tqdm riêng mỗi lần encode (và ép hiện bằng disable=False)."""

    def __init__(self, inner, stream):
        self.inner, self.stream = inner, stream

    def encode_docs(self, texts):
        from tqdm import tqdm
        for _ in tqdm(range(3), file=self.stream, desc="Inference Embeddings", disable=False):
            pass
        return self.inner.encode_docs(texts)

    def encode_queries(self, texts):
        return self.inner.encode_queries(texts)


def test_the_models_own_progress_bar_is_muted_so_only_one_bar_is_on_screen(tmp_path, shard, fake_cfg):
    """Nếu không tắt, mỗi lát sẽ in thêm một thanh của model đè lên thanh của pipeline."""
    import io

    class Tty(io.StringIO):
        def isatty(self): return True

    path, chunks = shard
    noise = Tty()
    st = encode_shard(path, tmp_path / "v.parquet", Noisy(build_embedder(fake_cfg), noise), fake_cfg)
    assert st.n_chunks == len(chunks)
    assert noise.getvalue() == ""