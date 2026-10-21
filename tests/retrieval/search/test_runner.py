import json
import pytest
from retrieval.results import Query, read_results
from retrieval.search import Retriever
from retrieval.search.runner import run_queries, run_select

QS = [Query(qid=7, text="triệu chứng của bệnh tiểu đường"), Query(qid=9, text="cao huyết áp đau đầu")]


def _run(run_world, tmp_path, qs=QS, collection=None):
    s, client, emb, rr = run_world
    out = tmp_path / "cand"
    return s, out, run_queries(s, Retriever(s, client, emb, rr, collection=collection), qs, out)


def _set_select(s, **over):
    s.retrieve = s.retrieve.model_copy(update=dict(select=s.retrieve.select.model_copy(update=over)))


def test_run_queries_writes_pool_candidates_and_card(run_world, tmp_path):
    s, out, res = _run(run_world, tmp_path)
    cands, pool = list(read_results(res["out"])), list(read_results(res["pool"]))
    assert [r.qid for r in cands] == [7, 9] and len(pool[0].candidates) >= len(cands[0].candidates) > 0
    assert cands[0].candidates[0].doc_id == "1" and res["failed"] == []
    card = json.loads((out / f"{res['run_id']}.run_card.json").read_text(encoding="utf-8"))
    assert card["n_queries"] == 2 and card["pool_file"].endswith(".pool.jsonl") and card["failed_qids"] == []


def test_file_names_follow_the_run_id(run_world, tmp_path):
    _, out, res = _run(run_world, tmp_path)
    rid = res["run_id"]
    assert res["out"] == out / f"{rid}.jsonl" and res["pool"] == out / f"{rid}.pool.jsonl"
    assert sorted(p.name for p in out.iterdir()) == sorted([f"{rid}.jsonl", f"{rid}.pool.jsonl", f"{rid}.run_card.json"])


def test_every_query_appears_in_order_with_its_text(run_world, tmp_path):
    qs = [Query(qid=9, text="cao huyết áp"), Query(qid=7, text="hen suyễn"), Query(qid=8, text="khó thở")]
    _, _, res = _run(run_world, tmp_path, qs)
    got = [(r.qid, r.query) for r in read_results(res["out"])]
    assert got == [(9, "cao huyết áp"), (7, "hen suyễn"), (8, "khó thở")]


def test_selection_is_applied_to_the_pool(run_world, tmp_path):
    s, _, res = _run(run_world, tmp_path)
    pool = {r.qid: r.candidates for r in read_results(res["pool"])}
    for r in read_results(res["out"]):
        pool_ids = {c.chunk_id for c in pool[r.qid]}
        assert {c.chunk_id for c in r.candidates} <= pool_ids
        assert len({c.doc_id for c in r.candidates}) <= s.retrieve.select.max_docs
        assert len(r.candidates) <= s.retrieve.select.max_docs * s.retrieve.select.chunks_per_doc


def test_pool_is_sorted_by_score(run_world, tmp_path):
    _, _, res = _run(run_world, tmp_path)
    for r in read_results(res["pool"]):
        assert [c.score for c in r.candidates] == sorted((c.score for c in r.candidates), reverse=True)


def test_output_directory_is_created_and_no_temp_files_remain(run_world, tmp_path):
    _, out, _ = _run(run_world, tmp_path)
    assert out.is_dir() and not list(out.glob("*.tmp"))


def test_card_records_the_thresholds_used(run_world, tmp_path):
    s = run_world[0]
    _set_select(s, max_docs=2, rel_drop=0.7)
    _, out, res = _run(run_world, tmp_path)
    card = json.loads((out / f"{res['run_id']}.run_card.json").read_text(encoding="utf-8"))
    assert card["retrieve"]["select"]["max_docs"] == 2 and card["retrieve"]["select"]["rel_drop"] == 0.7
    assert isinstance(card["seconds"], (int, float)) and card["run_id"] == res["run_id"]


def test_empty_query_list_writes_empty_files(run_world, tmp_path):
    _, out, res = _run(run_world, tmp_path, qs=[])
    assert list(read_results(res["out"])) == [] and list(read_results(res["pool"])) == []
    assert json.loads((out / f"{res['run_id']}.run_card.json").read_text())["n_queries"] == 0


# ---- truy vấn lỗi -----------------------------------------------------------------------------------------------

def test_failed_queries_still_appear_with_no_candidates_and_are_reported(run_world, tmp_path):
    _, out, res = _run(run_world, tmp_path, collection="không-có-collection")
    assert res["failed"] == [7, 9]
    rows = list(read_results(res["out"]))
    assert [(r.qid, r.candidates) for r in rows] == [(7, []), (9, [])]          # C2 luôn có đủ mọi qid
    card = json.loads((out / f"{res['run_id']}.run_card.json").read_text(encoding="utf-8"))
    assert card["failed_qids"] == [7, 9] and set(card["errors"]) == {"7", "9"} and all(card["errors"].values())


def test_only_the_failing_query_is_reported(run_world, tmp_path):
    s, client, emb, rr = run_world
    r = Retriever(s, client, emb, rr)
    orig = r.searcher.search
    state = {"n": 0}
    def flaky(vectors):
        state["n"] += 1
        if state["n"] == 2:
            raise RuntimeError("qdrant sập")
        return orig(vectors)
    r.searcher.search = flaky
    out = tmp_path / "cand"
    res = run_queries(s, r, QS, out)
    rows = {x.qid: x.candidates for x in read_results(res["out"])}
    assert res["failed"] == [QS[1].qid] and rows[7] and rows[9] == []
    card = json.loads((out / f"{res['run_id']}.run_card.json").read_text(encoding="utf-8"))
    assert "qdrant sập" in card["errors"][str(QS[1].qid)]


# ---- chọn lại từ pool -------------------------------------------------------------------------------------------

def test_run_select_reuses_pool_with_new_thresholds(run_world, tmp_path):
    s, out, res = _run(run_world, tmp_path)
    _set_select(s, max_docs=1, chunks_per_doc=1)
    res2 = run_select(s, res["pool"], out)
    for r in read_results(res2["out"]):
        assert len({c.doc_id for c in r.candidates}) == 1 and len(r.candidates) == 1


def test_run_select_does_not_touch_the_pool_and_needs_no_search_stack(run_world, tmp_path):
    s, out, res = _run(run_world, tmp_path)
    before = res["pool"].read_bytes()
    _set_select(s, max_docs=1)
    res2 = run_select(s, res["pool"], out)                       # chỉ cần settings + file pool (không client/embedder)
    assert res["pool"].read_bytes() == before and res2["run_id"] != res["run_id"]


def test_run_select_with_unchanged_thresholds_reproduces_the_candidates(run_world, tmp_path):
    s, out, res = _run(run_world, tmp_path)
    res2 = run_select(s, res["pool"], out)
    assert list(read_results(res2["out"])) == list(read_results(res["out"]))


def test_run_select_card_marks_reselection(run_world, tmp_path):
    s, out, res = _run(run_world, tmp_path)
    _set_select(s, max_docs=2)
    res2 = run_select(s, res["pool"], out)
    card = json.loads((out / f"{res2['run_id']}.run_card.json").read_text())
    assert card["reselected"] is True and card["n_queries"] == 2 and card["pool_file"] == res["pool"].name
    assert card["retrieve"]["select"]["max_docs"] == 2


def test_run_select_on_empty_pool(run_world, tmp_path):
    s, out, res = _run(run_world, tmp_path, qs=[])
    assert list(read_results(run_select(s, res["pool"], out)["out"])) == []


def test_run_select_missing_pool_raises(run_world, tmp_path):
    with pytest.raises(FileNotFoundError):
        run_select(run_world[0], tmp_path / "không_có.pool.jsonl", tmp_path)


# ---- pool phải đầy đủ (không phải kết quả đã chọn) --------------------------------------------------------------

def test_pool_keeps_candidates_that_the_selection_dropped(run_world, tmp_path):
    s = run_world[0]
    _set_select(s, max_docs=1, chunks_per_doc=1)
    _, _, res = _run(run_world, tmp_path)
    for sel, pool in zip(read_results(res["out"]), read_results(res["pool"])):
        assert len(sel.candidates) == 1 and len(pool.candidates) > 1


def test_selection_can_be_widened_later_from_the_same_pool(run_world, tmp_path):
    """Lý do tồn tại của run_select: chỉnh ngưỡng F2 mà không chạy lại GPU, nên pool phải còn đủ chunk để chọn rộng hơn."""
    s = run_world[0]
    _set_select(s, max_docs=1, chunks_per_doc=1)
    _, out, res = _run(run_world, tmp_path)
    _set_select(s, max_docs=3, chunks_per_doc=3, rel_drop=None)
    wider = list(read_results(run_select(s, res["pool"], out)["out"]))
    narrow = list(read_results(res["out"]))
    assert all(len(w.candidates) >= len(n.candidates) for w, n in zip(wider, narrow))
    assert any(len(w.candidates) > len(n.candidates) for w, n in zip(wider, narrow))