import pytest
from common.io import write_chunks, read_vectors
from factories import article
from retrieval.embedding import pending_jobs, embed_pending, build_embedder, measure_speed, RunSummary


class S:      # bộ cấu hình tối thiểu mà embed_pending cần
    def __init__(self, tmp, cfg): self.chunks_dir, self.vectors_dir, self.embed = tmp / "c", tmp / "v", cfg


@pytest.fixture
def env(tmp_path, chunker, fake_cfg):
    s = S(tmp_path, fake_cfg)
    for corpus, shard in [("viz", "s1"), ("viz", "s2"), ("en", "s1")]:
        d = s.chunks_dir / corpus; d.mkdir(parents=True, exist_ok=True)
        write_chunks(chunker.split(article(uid=f"vi:{len(list(d.iterdir())) + 1}")), d / f"{shard}.parquet")
    return s


def test_pending_lists_all_then_none_after_run(env):
    assert len(pending_jobs(env.chunks_dir, env.vectors_dir)) == 3
    r = embed_pending(env, build_embedder(env.embed))
    assert r.done == 3 and r.failed == [] and r.n_chunks > 0
    assert pending_jobs(env.chunks_dir, env.vectors_dir) == []
    assert (env.vectors_dir / "viz" / "s1.parquet").exists() and (env.vectors_dir / "en" / "s1.parquet").exists()


def test_vector_layout_mirrors_chunk_layout(env):
    for j in pending_jobs(env.chunks_dir, env.vectors_dir):
        assert j.vectors == env.vectors_dir / j.chunks.relative_to(env.chunks_dir)


def test_vectors_match_their_chunk_shard(env):
    from common.io import read_vector_ids, read_chunk_columns
    embed_pending(env, build_embedder(env.embed))
    for src in env.chunks_dir.rglob("*.parquet"):
        dst = env.vectors_dir / src.relative_to(env.chunks_dir)
        assert read_vector_ids(dst) == read_chunk_columns(src, ["chunk_id"])["chunk_id"]


def test_new_shard_only_is_processed(env, chunker):
    embed_pending(env, build_embedder(env.embed))
    write_chunks(chunker.split(article(uid="vi:77")), env.chunks_dir / "viz" / "s3.parquet")
    jobs = pending_jobs(env.chunks_dir, env.vectors_dir)
    assert [j.chunks.name for j in jobs] == ["s3.parquet"]


def test_second_run_does_nothing(env):
    emb = build_embedder(env.embed)
    embed_pending(env, emb)
    r = embed_pending(env, emb)
    assert (r.done, r.failed, r.n_chunks) == (0, [], 0)


def test_limit(env):
    assert embed_pending(env, build_embedder(env.embed), limit=1).done == 1


def test_failing_shard_does_not_stop_others(env):
    emb = build_embedder(env.embed)
    orig, state = emb.encode_docs, {"n": 0}
    def flaky(texts):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("boom")
        return orig(texts)
    emb.encode_docs = flaky
    r = embed_pending(env, emb)
    assert len(r.failed) == 1 and r.done == 2


def test_failed_shard_is_retried_on_the_next_run(env):
    emb = build_embedder(env.embed)
    orig, state = emb.encode_docs, {"fail": True}
    def flaky(texts):
        if state["fail"]:
            state["fail"] = False
            raise RuntimeError("boom")
        return orig(texts)
    emb.encode_docs = flaky
    r1 = embed_pending(env, emb)
    assert len(r1.failed) == 1 and len(pending_jobs(env.chunks_dir, env.vectors_dir)) == 1
    r2 = embed_pending(env, emb)
    assert r2.done == 1 and r2.failed == [] and pending_jobs(env.chunks_dir, env.vectors_dir) == []


def test_missing_chunks_dir(tmp_path):
    assert pending_jobs(tmp_path / "nope", tmp_path / "v") == []


def test_leftover_tmp_file_does_not_count_as_done(env):
    (env.vectors_dir / "viz").mkdir(parents=True)
    (env.vectors_dir / "viz" / "s1.tmp").write_text("dở dang", encoding="utf-8")
    assert len(pending_jobs(env.chunks_dir, env.vectors_dir)) == 3


def test_non_parquet_files_are_ignored(env):
    (env.chunks_dir / "viz" / "ghi_chu.txt").write_text("x")
    assert len(pending_jobs(env.chunks_dir, env.vectors_dir)) == 3


def test_new_vectors_dir_means_everything_is_pending_again(env, tmp_path):
    """embed_tag (hash cấu hình) nằm trong tên thư mục vectors: đổi cấu hình → thư mục mới → embed lại toàn bộ."""
    embed_pending(env, build_embedder(env.embed))
    assert len(pending_jobs(env.chunks_dir, tmp_path / "v_hash_khac")) == 3


def test_run_summary_speed():
    assert RunSummary(1, [], 100, 2.0).chunks_per_s == 50
    assert RunSummary(0, [], 0, 0.0).chunks_per_s == 0.0


def test_measure_speed(fake_cfg):
    assert measure_speed(build_embedder(fake_cfg), ["xin chào"] * 20) > 0


def test_measure_speed_excludes_warmup_call(fake_cfg):
    emb = build_embedder(fake_cfg)
    sizes, orig = [], emb.encode_docs
    emb.encode_docs = lambda texts: (sizes.append(len(texts)), orig(texts))[1]
    measure_speed(emb, ["a b"] * 10)
    assert sizes == [1, 10]