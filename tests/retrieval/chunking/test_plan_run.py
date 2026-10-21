import json
from types import SimpleNamespace
from common.io import read_chunks
from factories import article
from retrieval.chunking import pending_chunk_jobs, chunk_pending


def _write(p, docs):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(d.model_dump(), ensure_ascii=False) for d in docs) + "\n", encoding="utf-8")


def _s(tmp):
    return SimpleNamespace(env=SimpleNamespace(r2ai_corpus_dir=tmp / "corpus"), chunks_dir=tmp / "chunks")


def test_mirrors_layout_and_is_incremental(tmp_path, chunker):
    _write(tmp_path / "corpus/viz/docs/a/viz-a-0001.jsonl", [article(uid="vi:1")])
    _write(tmp_path / "corpus/viz/docs/b/viz-b-0001.jsonl", [article(uid="vi:2")])
    s = _s(tmp_path)
    assert len(pending_chunk_jobs(s.env.r2ai_corpus_dir, s.chunks_dir)) == 2
    r = chunk_pending(s, chunker)
    assert r.done == 2 and r.n_chunks > 0
    assert (tmp_path / "chunks/viz/docs/a/viz-a-0001.parquet").exists()
    assert pending_chunk_jobs(s.env.r2ai_corpus_dir, s.chunks_dir) == []
    _write(tmp_path / "corpus/viz/docs/a/viz-a-0002.jsonl", [article(uid="vi:3")])
    assert [j.chunks.name for j in pending_chunk_jobs(s.env.r2ai_corpus_dir, s.chunks_dir)] == ["viz-a-0002.parquet"]


def test_bad_shard_isolated(tmp_path, chunker):
    _write(tmp_path / "corpus/good.jsonl", [article(uid="vi:1")])
    (tmp_path / "corpus/bad.jsonl").write_text("{không phải json\n", encoding="utf-8")
    r = chunk_pending(_s(tmp_path), chunker)
    assert r.done == 1 and r.failed == ["bad.jsonl"]


def test_missing_corpus_dir(tmp_path):
    assert pending_chunk_jobs(tmp_path / "nope", tmp_path / "c") == []


def test_stem_variants():
    from pathlib import Path
    from retrieval.chunking.plan import _stem
    assert _stem(Path("a/viz-a-0001.jsonl.zst")) == "viz-a-0001" and _stem(Path("x.jsonl")) == "x" and _stem(Path("x.txt")) == "x"