from dataclasses import dataclass
from corpus_sync.report import scan_local, summarize_plan


@dataclass
class FileInfo:                 # khớp protocol _FileInfo (giống DryRunFileInfo của huggingface_hub)
    filename: str
    file_size: int | None
    will_download: bool = True


def info(filename: str, size: int | None, will_download: bool = True) -> FileInfo:
    return FileInfo(filename, size, will_download)


def test_summarize_plan_counts_only_files_that_will_download():
    infos = [info("corpus/viz/docs/a/s1.jsonl.zst", 1_000_000), info("corpus/viz/docs/a/s2.jsonl.zst", 2_000_000, False),
             info("queries/query.parquet", 50_000)]
    s = summarize_plan(infos)
    assert s.n_files == 3 and s.n_to_download == 2 and s.bytes_to_download == 1_050_000


def test_summarize_plan_groups_by_three_level_prefix():
    infos = [info("corpus/viz/docs/a/s1.jsonl.zst", 10), info("corpus/viz/docs/a/s2.jsonl.zst", 20),
             info("corpus/viz/docs/b/s1.jsonl.zst", 5), info("corpus/raw/links_corpus.parquet", 100),
             info("queries/query.parquet", 1)]
    s = summarize_plan(infos)
    assert s.by_prefix == {"corpus/raw/links_corpus.parquet": (1, 100), "corpus/viz/docs": (3, 35), "queries/query.parquet": (1, 1)}


def test_summarize_plan_missing_file_size_counts_as_zero_bytes():
    assert summarize_plan([info("a/b/c.jsonl.zst", None)]).bytes_to_download == 0


def test_summarize_plan_empty_input():
    s = summarize_plan([])
    assert (s.n_files, s.n_to_download, s.bytes_to_download, s.by_prefix) == (0, 0, 0, {})


def test_scan_local_counts_shards_per_partition_and_total_bytes(tmp_path):
    docs = tmp_path / "corpus" / "viz" / "docs"
    (docs / "a").mkdir(parents=True); (docs / "b").mkdir(parents=True)
    (docs / "a" / "viz-a-00001.jsonl.zst").write_bytes(b"x" * 10)
    (docs / "a" / "viz-a-00002.jsonl.zst").write_bytes(b"x" * 20)
    (docs / "b" / "viz-b-00001.jsonl.zst").write_bytes(b"x" * 5)
    links = tmp_path / "corpus" / "raw" / "links_corpus.parquet"; links.parent.mkdir(parents=True); links.write_bytes(b"x")
    s = scan_local(tmp_path / "corpus", tmp_path / "queries" / "query.parquet", links)
    assert s.n_shards == {"a": 2, "b": 1} and s.bytes_total == 35 and s.has_links is True and s.has_queries is False


def test_scan_local_ignores_stray_files_directly_under_docs_dir(tmp_path):
    docs = tmp_path / "corpus" / "viz" / "docs"
    (docs / "a").mkdir(parents=True)
    (docs / "a" / "viz-a-00001.jsonl.zst").write_bytes(b"x" * 10)
    (docs / "README.txt").write_bytes(b"not a partition")          # không phải thư mục phân vùng, không phải shard
    s = scan_local(tmp_path / "corpus", tmp_path / "q.parquet", tmp_path / "links.parquet")
    assert s.n_shards == {"a": 1} and s.bytes_total == 10


def test_scan_local_plain_jsonl_also_counted(tmp_path):
    docs = tmp_path / "corpus" / "viz" / "docs" / "a"; docs.mkdir(parents=True)
    (docs / "s.jsonl").write_bytes(b"x" * 7)
    s = scan_local(tmp_path / "corpus", tmp_path / "q.parquet", tmp_path / "links.parquet")
    assert s.n_shards == {"a": 1} and s.bytes_total == 7


def test_scan_local_missing_corpus_dir_is_empty_not_an_error(tmp_path):
    s = scan_local(tmp_path / "không-tồn-tại", tmp_path / "q.parquet", tmp_path / "links.parquet")
    assert s.n_shards == {} and s.bytes_total == 0 and not s.has_links and not s.has_queries