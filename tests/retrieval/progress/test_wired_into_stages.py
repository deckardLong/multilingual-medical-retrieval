import json
from types import SimpleNamespace
import pytest
from factories import article
from retrieval.chunking import chunk_pending
from retrieval.embedding import embed_pending


class RecordingBar:
    def __init__(self, log, desc, total, unit):
        self.log, self.desc, self.total, self.unit = log, desc, total, unit
        self.n, self.labels, self.open = 0, [], False

    def __enter__(self):
        self.open = True
        self.log.append(self)
        assert sum(1 for b in self.log if b.open) == 1, "hai thanh cùng sống một lúc sẽ chồng dòng lên nhau"
        return self

    def __exit__(self, *exc):
        self.open = False
        return False

    def advance(self, n=1): self.n += n
    def where(self, label): self.labels.append(label)


@pytest.fixture
def bars():
    """(log, make_bar): mọi thanh được tạo đều nằm trong log để test soi lại."""
    log = []
    return log, lambda desc, total, unit="it": RecordingBar(log, desc, total, unit)


@pytest.fixture
def world_dirs(tmp_path, fake_cfg):
    """Kho 2 shard doc (mỗi shard 1 bài, chunk ra nhiều chunk) cùng settings tối thiểu cho chunk/embed."""
    for part, uid in (("a", "vi:1"), ("b", "vi:2")):
        p = tmp_path / "corpus" / "viz" / "docs" / part / f"viz-{part}-0001.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(article(uid=uid).model_dump(), ensure_ascii=False) + "\n", encoding="utf-8")
    s = SimpleNamespace(env=SimpleNamespace(r2ai_corpus_dir=tmp_path / "corpus"), chunks_dir=tmp_path / "chunks",
                        vectors_dir=tmp_path / "vectors", embed=fake_cfg)
    return s, tmp_path


def test_embed_stage_counts_chunks_not_shards(world_dirs, chunker, fake_cfg, bars):
    from retrieval.embedding import build_embedder
    s, _ = world_dirs
    chunk_pending(s, chunker)
    log, make_bar = bars
    out = embed_pending(s, build_embedder(fake_cfg), make_bar=make_bar)
    (bar,) = log
    assert bar.desc == "embed" and bar.unit == "chunk"
    assert bar.total == bar.n == out.n_chunks > out.done and not bar.open


def test_a_failing_shard_still_advances_the_chunk_bar(world_dirs, chunker, bars, monkeypatch):
    """Nếu shard lỗi mà không advance, thanh sẽ đứng im và không bao giờ đầy."""
    import retrieval.chunking.run as run_module
    s, _ = world_dirs
    good, calls = run_module.chunk_shard, {"n": 0}

    def flaky(shard, out, chunker):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("shard hỏng")
        return good(shard, out, chunker)

    monkeypatch.setattr(run_module, "chunk_shard", flaky)
    log, make_bar = bars
    out = chunk_pending(s, chunker, make_bar=make_bar)
    (bar,) = log
    assert len(out.failed) == 1 and out.done == 1 and bar.n == bar.total == 2