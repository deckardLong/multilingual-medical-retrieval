import json
import pytest
from common.io import read_chunks
from retrieval.chunking import chunk_shard, ChunkingError
from factories import article


def _write(path, docs):
    path.write_text("\n".join(json.dumps(d.model_dump(), ensure_ascii=False) for d in docs) + "\n", encoding="utf-8")


def test_chunk_shard_writes_parquet_and_stats(tmp_path, chunker):
    docs = [article(uid=f"vi:{i}") for i in range(1, 4)] + [article(uid="vi:9").model_copy(update=dict(text="Chỉ tiêu đề"))]
    src = tmp_path / "s.jsonl"; _write(src, docs)
    out = tmp_path / "out" / "s.parquet"
    out.parent.mkdir()
    st = chunk_shard(src, out, chunker)
    rows = read_chunks(out)
    assert st.n_docs == 4 and st.n_empty_docs == 1 and st.n_chunks == len(rows) > 0
    assert st.max_tokens >= st.mean_tokens > 0
    assert {r["uid"] for r in rows} == {"vi:1", "vi:2", "vi:3"}


def test_chunk_shard_aborts_without_partial_file(tmp_path, chunker):
    src = tmp_path / "s.jsonl"; _write(src, [article()])
    class Bad:
        def split(self, doc):
            cs = chunker.split(doc)
            return [cs[0].model_copy(update=dict(text="không khớp"))] + cs[1:]
    out = tmp_path / "o.parquet"
    with pytest.raises(ChunkingError):
        chunk_shard(src, out, Bad())
    assert not out.exists()