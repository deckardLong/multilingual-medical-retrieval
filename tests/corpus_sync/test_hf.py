"""Không gọi mạng thật: snapshot_download được giả lập bằng cách ghi file trực tiếp vào thư mục đệm."""
from pathlib import Path
import pytest
import corpus_sync.hf as hf_module
from corpus_sync.hf import fetch, place, plan


@pytest.fixture
def no_network(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    monkeypatch.setattr(hf_module, "STAGING", staging)
    calls = []

    def fake_snapshot_download(repo_id, *, repo_type, revision, local_dir, allow_patterns, max_workers, token,
                               dry_run=False):
        calls.append(dict(repo_id=repo_id, repo_type=repo_type, revision=revision, local_dir=local_dir,
                          allow_patterns=allow_patterns, max_workers=max_workers, token=token, dry_run=dry_run))
        if dry_run:
            return []
        local_dir = Path(local_dir)
        (local_dir / "corpus" / "viz" / "docs" / "a").mkdir(parents=True, exist_ok=True)
        (local_dir / "corpus" / "viz" / "docs" / "a" / "viz-a-00001.jsonl.zst").write_bytes(b"shard-noi-dung")
        (local_dir / "corpus" / "raw").mkdir(parents=True, exist_ok=True)
        (local_dir / "corpus" / "raw" / "links_corpus.parquet").write_bytes(b"links")
        (local_dir / "queries").mkdir(parents=True, exist_ok=True)
        (local_dir / "queries" / "query.parquet").write_bytes(b"queries")
        return local_dir

    monkeypatch.setattr(hf_module, "snapshot_download", fake_snapshot_download)
    return staging, calls


def test_fetch_places_corpus_and_queries_at_their_configured_destinations(sync_cfg, tmp_path, no_network):
    from common.config import Env
    env = Env(r2ai_corpus_dir=tmp_path / "my_corpus")
    fetch(sync_cfg, env, queries_dir=tmp_path / "my_queries")
    assert (env.r2ai_corpus_dir / "viz" / "docs" / "a" / "viz-a-00001.jsonl.zst").read_bytes() == b"shard-noi-dung"
    assert (env.r2ai_corpus_dir / "raw" / "links_corpus.parquet").read_bytes() == b"links"
    assert (tmp_path / "my_queries" / "query.parquet").read_bytes() == b"queries"


def test_fetch_passes_repo_id_patterns_and_token_through(sync_cfg, tmp_path, no_network):
    from common.config import Env
    env = Env(r2ai_corpus_dir=tmp_path / "c", hf_token="shh")
    fetch(sync_cfg, env, patterns=["queries/query.parquet"], queries_dir=tmp_path / "q")
    staging, calls = no_network
    assert calls[0]["repo_id"] == sync_cfg.repo_id and calls[0]["allow_patterns"] == ["queries/query.parquet"]
    assert calls[0]["token"] == "shh" and calls[0]["dry_run"] is False


def test_fetch_defaults_to_the_configured_patterns_when_none_given(sync_cfg, tmp_path, no_network):
    from common.config import Env
    fetch(sync_cfg, Env(r2ai_corpus_dir=tmp_path / "c"), queries_dir=tmp_path / "q")
    assert no_network[1][0]["allow_patterns"] == sync_cfg.allow_patterns


def test_plan_calls_snapshot_download_with_dry_run_true_and_downloads_nothing(sync_cfg, tmp_path, no_network):
    from common.config import Env
    out = plan(sync_cfg, Env(r2ai_corpus_dir=tmp_path / "c", hf_token="shh"))
    assert out == [] and no_network[1][0]["dry_run"] is True and no_network[1][0]["token"] == "shh"
    assert not (tmp_path / "c").exists()


# ---- place() tự nó -------------------------------------------------------------------------------------------

def test_place_copies_new_files_preserving_structure(tmp_path):
    src = tmp_path / "src"; (src / "a").mkdir(parents=True)
    (src / "a" / "f.txt").write_bytes(b"noi dung")
    dst = tmp_path / "dst"
    assert place(src, dst) == 1
    assert (dst / "a" / "f.txt").read_bytes() == b"noi dung"


def test_place_skips_files_already_present_with_the_same_size(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "f.txt").write_bytes(b"1234")
    dst = tmp_path / "dst"; dst.mkdir()
    (dst / "f.txt").write_bytes(b"ABCD")             # cùng kích thước, nội dung khác — vẫn coi là "đã có"
    assert place(src, dst) == 0 and (dst / "f.txt").read_bytes() == b"ABCD"


def test_place_overwrites_files_whose_size_changed(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "f.txt").write_bytes(b"123456")
    dst = tmp_path / "dst"; dst.mkdir()
    (dst / "f.txt").write_bytes(b"ab")
    assert place(src, dst) == 1 and (dst / "f.txt").read_bytes() == b"123456"


def test_place_missing_source_is_a_no_op(tmp_path):
    assert place(tmp_path / "không-có", tmp_path / "dst") == 0 and not (tmp_path / "dst").exists()


def test_place_only_copies_files_not_empty_directories(tmp_path):
    src = tmp_path / "src"; (src / "empty_dir").mkdir(parents=True)
    assert place(src, tmp_path / "dst") == 0