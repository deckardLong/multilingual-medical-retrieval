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


# ---- resume -----------------------------------------------------------------------------------------------------

def _interrupted_run(run_world, out, qs, stop_at):
    s, client, emb, rr = run_world
    r = Retriever(s, client, emb, rr)
    orig, n = r.searcher.search, {"n": 0}
    def search(vectors):
        n["n"] += 1
        if n["n"] == stop_at:
            raise KeyboardInterrupt
        return orig(vectors)
    r.searcher.search = search
    with pytest.raises(KeyboardInterrupt):
        run_queries(s, r, qs, out)
    return s


def test_interrupted_run_resumes_with_only_the_missing_queries(run_world, tmp_path):
    out = tmp_path / "cand"
    s = _interrupted_run(run_world, out, QS, stop_at=2)
    assert len(list(out.glob(".resume-*.jsonl"))) == 1 and not list(out.glob("*.pool.jsonl"))
    _, client, emb, rr = run_world
    r = Retriever(s, client, emb, rr)
    orig, calls = r.searcher.search, []
    r.searcher.search = lambda v: (calls.append(1), orig(v))[1]
    res = run_queries(s, r, QS, out)
    assert len(calls) == 1 and res["failed"] == []
    assert [x.qid for x in read_results(res["out"])] == [7, 9] and all(x.candidates for x in read_results(res["pool"]))
    assert json.loads((out / f"{res['run_id']}.run_card.json").read_text(encoding="utf-8"))["resumed"] == 1
    assert not list(out.glob(".resume-*.jsonl"))


def test_resumed_result_equals_an_uninterrupted_run(run_world, tmp_path):
    s = _interrupted_run(run_world, tmp_path / "a", QS, stop_at=2)
    _, client, emb, rr = run_world
    resumed = run_queries(s, Retriever(s, client, emb, rr), QS, tmp_path / "a")
    fresh = run_queries(s, Retriever(s, client, emb, rr), QS, tmp_path / "b")
    assert list(read_results(resumed["pool"])) == list(read_results(fresh["pool"]))


def test_fresh_flag_ignores_the_checkpoint(run_world, tmp_path):
    out = tmp_path / "cand"
    s = _interrupted_run(run_world, out, QS, stop_at=2)
    _, client, emb, rr = run_world
    r = Retriever(s, client, emb, rr)
    orig, calls = r.searcher.search, []
    r.searcher.search = lambda v: (calls.append(1), orig(v))[1]
    run_queries(s, r, QS, out, resume=False)
    assert len(calls) == 2


def test_changed_query_text_is_not_taken_from_the_checkpoint(run_world, tmp_path):
    out = tmp_path / "cand"
    s = _interrupted_run(run_world, out, QS, stop_at=2)
    _, client, emb, rr = run_world
    r = Retriever(s, client, emb, rr)
    orig, calls = r.searcher.search, []
    r.searcher.search = lambda v: (calls.append(1), orig(v))[1]
    run_queries(s, r, [Query(qid=7, text="hen suyễn khó thở"), QS[1]], out)
    assert len(calls) == 2


def test_failed_queries_are_retried_on_the_next_run(run_world, tmp_path):
    s, client, emb, rr = run_world
    out = tmp_path / "cand"
    r = Retriever(s, client, emb, rr)
    orig, n = r.searcher.search, {"n": 0}
    def flaky(v):
        n["n"] += 1
        if n["n"] == 2:
            raise RuntimeError("qdrant sập")
        return orig(v)
    r.searcher.search = flaky
    assert run_queries(s, r, QS, out)["failed"] == [9]
    assert len(list(out.glob(".resume-*.jsonl"))) == 1
    res = run_queries(s, Retriever(s, client, emb, rr), QS, out)
    assert res["failed"] == [] and all(x.candidates for x in read_results(res["pool"]))


def test_checkpoint_skips_a_torn_last_line_and_keeps_appending_cleanly(tmp_path):
    from retrieval.results import QueryResult
    from retrieval.search.checkpoint import Checkpoint
    path = tmp_path / "ck.jsonl"
    ck = Checkpoint(path)
    ck.add(QueryResult(qid=1, query="a", candidates=[])); ck.close()
    with open(path, "a", encoding="utf-8") as f:
        f.write('{"qid": 2, "query": "b", "candid')
    ck = Checkpoint(path)
    assert set(ck.load([Query(qid=1, text="a"), Query(qid=2, text="b")])) == {1}
    ck.add(QueryResult(qid=2, query="b", candidates=[])); ck.close()
    assert set(Checkpoint(path).load([Query(qid=1, text="a"), Query(qid=2, text="b")])) == {1, 2}


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