import sys
import pytest
from corpus_sync import run_fetch
from corpus_sync.settings import SyncCfg

BASE = ["corpus/viz/docs/**/*.jsonl.zst", "corpus/raw/links_corpus.parquet", "corpus/schema/*.json", "queries/query.parquet"]


def cfg(**kw):
    return SyncCfg(repo_id="o/r", repo_type="dataset", revision="main", allow_patterns=list(BASE), max_workers=4, **kw)


@pytest.mark.parametrize("args,expected", [
    ([], BASE),
    (["--no-docs"], [p for p in BASE if "viz/docs" not in p]),
    (["--partition", "a"], ["corpus/viz/docs/a/**/*.jsonl.zst", *BASE[1:]]),
    (["--queries-only"], ["queries/query.parquet"]),
])
def test_patterns_follow_the_cli_flags(args, expected):
    a = run_fetch.argparse.ArgumentParser()
    a.add_argument("--dry-run", action="store_true"); a.add_argument("--partition", choices=["a", "b"], default=None)
    a.add_argument("--no-docs", action="store_true"); a.add_argument("--queries-only", action="store_true")
    ns = a.parse_args(args)
    assert run_fetch._patterns(cfg(), ns) == expected


@pytest.fixture
def cli(monkeypatch, cfg_dir, tmp_path):
    """Cô lập hoàn toàn khỏi thư mục dự án thật: R2AI_CORPUS_DIR và run_fetch.ROOT (nơi main() tìm queries/) đều
    trỏ vào tmp_path. fetch()/plan() được giả lập — không gọi mạng, không chạm vào kho thật."""
    monkeypatch.setenv("R2AI_CORPUS_DIR", str(tmp_path / "corpus"))
    monkeypatch.setattr(run_fetch, "ROOT", tmp_path)
    calls = {}

    def fake_fetch(cfg, env, patterns=None):
        calls["fetch"] = (cfg.repo_id, patterns)
        if any("viz/docs" in p for p in (patterns or [])):
            docs = env.r2ai_corpus_dir / "viz" / "docs" / "a"; docs.mkdir(parents=True)
            (docs / "viz-a-00001.jsonl.zst").write_bytes(b"x" * 9)
        if any("links_corpus.parquet" in p for p in (patterns or [])):
            (env.r2ai_corpus_dir / "raw").mkdir(parents=True)
            (env.r2ai_corpus_dir / "raw" / "links_corpus.parquet").write_bytes(b"x")
        if any(p.endswith("query.parquet") for p in (patterns or [])):
            (tmp_path / "queries").mkdir(parents=True, exist_ok=True)
            (tmp_path / "queries" / "query.parquet").write_bytes(b"x")

    def fake_plan(cfg, env, patterns=None):
        calls["plan"] = (cfg.repo_id, patterns)
        return []

    monkeypatch.setattr(run_fetch, "fetch", fake_fetch)
    monkeypatch.setattr(run_fetch, "plan", fake_plan)
    return calls


def run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["prog", *args])
    return run_fetch.main()


def test_default_run_fetches_everything_and_exits_zero(cli, monkeypatch, capsys):
    assert run(monkeypatch) == 0
    out = capsys.readouterr().out
    assert "fetch" in cli and "'a': 1" in out and "links_corpus.parquet: có" in out and "query.parquet: có" in out


def test_dry_run_does_not_fetch_and_reports_nothing_to_download(cli, monkeypatch, capsys):
    assert run(monkeypatch, "--dry-run") == 0
    assert "plan" in cli and "fetch" not in cli
    assert "0/0 file" in capsys.readouterr().out


def test_dry_run_prints_a_line_per_prefix_with_files_to_download(cli, monkeypatch, capsys):
    from types import SimpleNamespace

    def fake_plan(cfg, env, patterns=None):
        return [SimpleNamespace(filename="corpus/viz/docs/a/s1.jsonl.zst", file_size=1_000_000, will_download=True)]

    monkeypatch.setattr(run_fetch, "plan", fake_plan)
    assert run(monkeypatch, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "1/1 file" in out and "corpus/viz/docs: 1 file, 1.0 MB" in out


def test_partition_flag_is_forwarded_to_fetch(cli, monkeypatch):
    run(monkeypatch, "--partition", "b")
    assert cli["fetch"][1] == ["corpus/viz/docs/b/**/*.jsonl.zst", "corpus/raw/links_corpus.parquet",
                               "corpus/schema/*.json", "queries/query.parquet"]


def test_queries_only_succeeds_without_fetching_docs_or_links(cli, monkeypatch, capsys):
    assert run(monkeypatch, "--queries-only") == 0
    out = capsys.readouterr().out
    assert "query.parquet: có" in out and "links_corpus.parquet: CHƯA CÓ" in out   # không xin links, không bị phạt


def test_no_docs_skips_shards_but_still_checks_links_and_queries(cli, monkeypatch, capsys):
    assert run(monkeypatch, "--no-docs") == 0
    out = capsys.readouterr().out
    assert cli["fetch"][1] == [p for p in BASE if "viz/docs" not in p]
    assert "shard theo phân vùng: {}" in out and "links_corpus.parquet: có" in out and "query.parquet: có" in out


def test_exit_code_is_nonzero_when_everything_requested_is_still_missing(monkeypatch, cfg_dir, tmp_path):
    """fetch() không ghi gì (giả lập tải lỗi/thiếu quyền) dù patterns mặc định có xin cả hai — phải báo lỗi."""
    monkeypatch.setenv("R2AI_CORPUS_DIR", str(tmp_path / "corpus"))
    monkeypatch.setattr(run_fetch, "ROOT", tmp_path)
    monkeypatch.setattr(run_fetch, "fetch", lambda cfg, env, patterns=None: None)
    assert run(monkeypatch) == 1


def test_exit_code_is_nonzero_when_only_links_are_still_missing(monkeypatch, cfg_dir, tmp_path):
    monkeypatch.setenv("R2AI_CORPUS_DIR", str(tmp_path / "corpus"))
    monkeypatch.setattr(run_fetch, "ROOT", tmp_path)

    def fetch_without_links(cfg, env, patterns=None):
        (tmp_path / "queries").mkdir(parents=True); (tmp_path / "queries" / "query.parquet").write_bytes(b"x")
        # không ghi corpus/raw/links_corpus.parquet dù patterns mặc định có xin nó

    monkeypatch.setattr(run_fetch, "fetch", fetch_without_links)
    assert run(monkeypatch) == 1


def test_exit_code_is_nonzero_when_only_queries_are_still_missing(monkeypatch, cfg_dir, tmp_path):
    monkeypatch.setenv("R2AI_CORPUS_DIR", str(tmp_path / "corpus"))
    monkeypatch.setattr(run_fetch, "ROOT", tmp_path)

    def fetch_without_queries(cfg, env, patterns=None):
        (env.r2ai_corpus_dir / "raw").mkdir(parents=True)
        (env.r2ai_corpus_dir / "raw" / "links_corpus.parquet").write_bytes(b"x")
        # không ghi queries/query.parquet dù patterns mặc định có xin nó

    monkeypatch.setattr(run_fetch, "fetch", fetch_without_queries)
    assert run(monkeypatch) == 1