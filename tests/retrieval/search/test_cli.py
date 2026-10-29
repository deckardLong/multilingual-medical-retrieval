"""run_queries.main / run_select.main: gắn bộ phận thật bằng monkeypatch (không cần Qdrant server, GPU, .env)."""
import sys
import pyarrow as pa, pyarrow.parquet as pq
import pytest
from retrieval import run_queries as rq, run_select as rs
from retrieval.results import read_results
from retrieval.search import Retriever


@pytest.fixture
def cli(monkeypatch, run_world, tmp_path):
    s, client, emb, rr = run_world
    monkeypatch.setattr(rq, "load_all", lambda env: s)
    monkeypatch.setattr(rq, "make_client", lambda env: client)
    monkeypatch.setattr(rq, "build_embedder", lambda cfg: emb)
    monkeypatch.setattr(rq, "build_reranker", lambda cfg: rr)
    monkeypatch.setattr(rs, "load_all", lambda env: s)
    seen = {}
    def recording_retriever(settings, c, e, r, collection=None):
        seen["collection"] = collection
        return Retriever(settings, c, e, r, collection=collection)
    monkeypatch.setattr(rq, "Retriever", recording_retriever)
    out = tmp_path / "out"
    return SimpleCli(monkeypatch, s, out, seen, tmp_path)


class SimpleCli:
    def __init__(self, monkeypatch, s, out, seen, tmp_path):
        self.mp, self.s, self.out, self.seen, self.tmp = monkeypatch, s, out, seen, tmp_path

    def queries(self, ids, texts, id_col="id", text_col="query"):
        p = self.tmp / "q.parquet"
        pq.write_table(pa.table({id_col: ids, text_col: texts}), p)
        return str(p)

    def run(self, module, *args):
        self.mp.setattr(sys, "argv", ["prog", *args])
        return module.main()


def test_run_queries_success_writes_files_and_exits_zero(cli, capsys):
    q = cli.queries([1, 2], ["bệnh tiểu đường", "cao huyết áp"])
    assert cli.run(rq, "--queries", q, "--out-dir", str(cli.out)) == 0
    assert "→" in capsys.readouterr().out
    assert len(list(cli.out.glob("*.jsonl"))) == 2 and len(list(cli.out.glob("*.run_card.json"))) == 1


def test_limit_restricts_the_number_of_queries(cli):
    q = cli.queries([1, 2, 3], ["bệnh tiểu đường", "cao huyết áp", "hen suyễn"])
    cli.run(rq, "--queries", q, "--limit", "2", "--out-dir", str(cli.out))
    (out_file,) = [p for p in cli.out.glob("*.jsonl") if not p.name.endswith(".pool.jsonl")]
    assert [r.qid for r in read_results(out_file)] == [1, 2]


def test_custom_column_names(cli):
    q = cli.queries([5], ["bệnh tiểu đường"], id_col="qid", text_col="text")
    assert cli.run(rq, "--queries", q, "--id-col", "qid", "--text-col", "text", "--out-dir", str(cli.out)) == 0


def test_failing_query_gives_exit_code_one(cli, capsys):
    cli.s.collection = "không-có-collection"
    q = cli.queries([1], ["bệnh tiểu đường"])
    assert cli.run(rq, "--queries", q, "--out-dir", str(cli.out)) == 1
    assert "[1]" in capsys.readouterr().out


def test_live_flag_searches_the_alias(cli):
    q = cli.queries([1], ["bệnh tiểu đường"])
    cli.run(rq, "--queries", q, "--out-dir", str(cli.out))
    assert cli.seen["collection"] is None                                     # mặc định: collection theo cấu hình
    cli.run(rq, "--queries", q, "--out-dir", str(cli.out), "--live")
    assert cli.seen["collection"] == cli.s.index.alias


def test_wrong_column_name_is_an_error(cli):
    q = cli.queries([1], ["bệnh tiểu đường"])
    with pytest.raises(ValueError, match="cột"):
        cli.run(rq, "--queries", q, "--text-col", "nope", "--out-dir", str(cli.out))


def test_blank_query_text_is_rejected_instead_of_searched(cli):
    q = cli.queries([1, 2], ["bệnh tiểu đường", None])
    with pytest.raises(ValueError, match="rỗng"):
        cli.run(rq, "--queries", q, "--out-dir", str(cli.out))
    assert not cli.out.exists() or not list(cli.out.glob("*.jsonl"))


def test_run_select_main(cli, capsys):
    q = cli.queries([1, 2], ["bệnh tiểu đường", "cao huyết áp"])
    cli.run(rq, "--queries", q, "--out-dir", str(cli.out))
    (pool,) = cli.out.glob("*.pool.jsonl")
    assert cli.run(rs, "--pool", str(pool), "--out-dir", str(cli.out / "re")) == 0
    assert "→" in capsys.readouterr().out and len(list((cli.out / "re").glob("*.jsonl"))) == 1


def test_run_select_defaults_to_the_newest_pool(cli, capsys):
    q = cli.queries([1, 2], ["bệnh tiểu đường", "cao huyết áp"])
    cli.run(rq, "--queries", q, "--out-dir", str(cli.out))
    (pool,) = cli.out.glob("*.pool.jsonl")
    assert cli.run(rs, "--out-dir", str(cli.out)) == 0
    assert pool.name in capsys.readouterr().out


def test_run_select_without_any_pool_says_so(cli, tmp_path):
    with pytest.raises(FileNotFoundError, match="run_queries"):
        cli.run(rs, "--out-dir", str(tmp_path / "trống"))