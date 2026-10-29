"""python -m submission.run_submit: cấu hình trỏ vào thư mục tạm để không ghi nhật ký/đọc dữ liệu thật của repo."""
import csv, json, sys, zipfile
import pytest, yaml
from factories import cand_of
from retrieval.results import QueryResult, write_results
from submission import run_submit
from submission.pack import read_zip


@pytest.fixture
def cli(cfg_dir, tmp_path, monkeypatch):
    p = cfg_dir / "submit.yaml"
    cfg = yaml.safe_load(p.read_text("utf-8"))
    cfg.update(output_dir=str(tmp_path / "subs"), log_csv=str(tmp_path / "log.csv"), candidates_path=str(tmp_path / "c.jsonl"))
    cfg["check"]["btc_ids_path"] = str(tmp_path / "ids.jsonl")
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), "utf-8")

    (tmp_path / "ids.jsonl").write_text("\n".join(json.dumps({"id": i, "url": f"u{i}"}) for i in (1, 2, 3)), "utf-8")
    (tmp_path / "q.jsonl").write_text("\n".join(json.dumps({"id": i, "query": f"câu {i}"}) for i in (1, 2)), "utf-8")
    write_results(tmp_path / "c.jsonl", [
        QueryResult(qid=1, query="câu 1", candidates=[cand_of("vi:1", 0, "triệu chứng")]),
        QueryResult(qid=2, query="câu 2", candidates=[cand_of("zh:2", 0, "糖尿病"), cand_of("en:3", 0, "pubmed")])])

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["prog", "--queries", str(tmp_path / "q.jsonl"), *args])
        return run_submit.main()
    return run, tmp_path


def test_success_creates_zip_log_and_prints_summary(cli, capsys):
    run, tmp = cli
    assert run() == 0
    out = capsys.readouterr().out
    assert "c.zip" in out and "2 truy vấn, 3 doc, 3 chunk, 0 truy vấn trống" in out
    items = read_zip(tmp / "subs" / "c.zip")
    assert [i.id for i in items] == [1, 2] and items[1].relevant_docs == ["2", "3"]
    (row,) = csv.DictReader(open(tmp / "log.csv", encoding="utf-8", newline=""))
    assert row["zip"] == "c.zip" and row["n_queries"] == "2"


def test_missing_query_exits_with_one_and_writes_nothing(cli, capsys):
    run, tmp = cli
    (tmp / "q.jsonl").write_text("\n".join(json.dumps({"id": i, "query": "x"}) for i in (1, 2, 3)), "utf-8")
    assert run() == 1
    assert "thiếu 1" in capsys.readouterr().out and not (tmp / "subs").exists() and not (tmp / "log.csv").exists()


def test_unknown_btc_id_is_dropped_and_warned(cli, capsys):
    run, tmp = cli
    (tmp / "ids.jsonl").write_text("\n".join(json.dumps({"id": i, "url": "u"}) for i in (1, 3)), "utf-8")   # thiếu id 2
    assert run() == 0 and "không thuộc danh sách" in capsys.readouterr().out
    assert read_zip(tmp / "subs" / "c.zip")[1].relevant_docs == ["3"]


def test_absent_id_list_only_warns(cli, capsys):
    run, tmp = cli
    (tmp / "ids.jsonl").unlink()
    assert run() == 0 and "WARNING" in capsys.readouterr().out


def test_name_note_and_out_dir_options(cli):
    run, tmp = cli
    assert run("--name", "lan_2", "--note", "rel_drop 0.5", "--out-dir", str(tmp / "khac")) == 0
    assert (tmp / "khac" / "lan_2.zip").exists()
    (row,) = csv.DictReader(open(tmp / "log.csv", encoding="utf-8", newline=""))
    assert row["note"] == "rel_drop 0.5"


def test_explicit_candidates_path_and_name_default_to_its_stem(cli):
    run, tmp = cli
    (tmp / "c.jsonl").rename(tmp / "run20261020.jsonl")
    assert run("--candidates", str(tmp / "run20261020.jsonl")) == 0
    assert (tmp / "subs" / "run20261020.zip").exists()


def test_the_zip_is_what_the_leaderboard_expects(cli):
    run, tmp = cli
    run()
    with zipfile.ZipFile(tmp / "subs" / "c.zip") as z:
        (name,) = z.namelist()
        data = json.loads(z.read(name))
    assert name == "submission.json" and sorted(data[0]) == ["id", "relevant_chunks", "relevant_docs"]
    assert data[1]["relevant_docs"] == [2, 3] and data[1]["relevant_chunks"][0]["doc_id"] == 2   # BTC chấm doc_id dạng số