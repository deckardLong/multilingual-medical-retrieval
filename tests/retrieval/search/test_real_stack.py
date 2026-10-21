"""Chuỗi THẬT từ đầu đến cuối: BGE-M3 + bge-reranker + Qdrant (trong bộ nhớ). Mặc định bị bỏ qua; chạy trên máy có GPU:
    R2AI_TEST_REAL_MODEL=1 pytest -m gpu tests/retrieval/search/test_real_stack.py
Câu hỏi các test này trả lời: truy vấn tiếng Việt / Anh / Trung có tìm ra bài ĐÚNG KHÁI NIỆM ở ngôn ngữ khác không
(sỏi thận ↔ kidney stones ↔ 肾结石, như slide BTC)."""
import json, os
from types import SimpleNamespace
import pytest

pytestmark = [pytest.mark.gpu,
              pytest.mark.skipif(os.environ.get("R2AI_TEST_REAL_MODEL") != "1", reason="cần model thật + GPU")]

CORPUS = {
    "vi:1": ("Sỏi thận", "Sỏi thận gây đau dữ dội ở vùng hông lưng, buồn nôn và tiểu ra máu.\nUống nhiều nước giúp ngăn ngừa sỏi thận."),
    "zh:2": ("肾结石", "肾结石会引起腰部剧烈疼痛、恶心和血尿。\n多喝水有助于预防肾结石。"),
    "vi:3": ("Bóng đá", "Giải bóng đá quốc gia bắt đầu vào tháng tám.\nCác đội thi đấu hai mươi vòng."),
    "zh:4": ("足球", "足球联赛将于八月开始。\n各队将进行二十轮比赛。"),
}
KIDNEY, FOOTBALL = {"1", "2"}, {"3", "4"}


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    from qdrant_client import QdrantClient
    from common.config import Env
    from common.schema import Doc
    from retrieval.chunking import build_chunker, build_counter
    from retrieval.embedding import build_embedder
    from retrieval.index import Manifest
    from retrieval.pipeline import run_cycle
    from retrieval.rerank import build_reranker
    from retrieval.search import Retriever
    from retrieval.settings import load_all

    tmp = tmp_path_factory.mktemp("real_stack")
    st = load_all(Env())
    corpus = tmp / "corpus"; corpus.mkdir()
    docs = [Doc(uid=u, doc_id=u.split(":")[1], lang=u.split(":")[0], url="u", title=t, text=f"{t}\n{b}\n") for u, (t, b) in CORPUS.items()]
    (corpus / "s.jsonl").write_text("\n".join(json.dumps(d.model_dump(), ensure_ascii=False) for d in docs) + "\n", encoding="utf-8")
    s = SimpleNamespace(env=SimpleNamespace(r2ai_corpus_dir=corpus), chunks_dir=tmp / "c", vectors_dir=tmp / "v",
                        collection="real", index=st.index, embed=st.embed, retrieve=st.retrieve, rerank=st.rerank)
    chunker, emb, client = build_chunker(st.chunk, build_counter("approx"), st.chunk_tag), build_embedder(st.embed), QdrantClient(":memory:")
    run_cycle(s, client, Manifest(tmp / "m.jsonl"), lambda: chunker, lambda: emb)
    return Retriever(s, client, emb, build_reranker(st.rerank)), s


def _top_docs(stack, query, n=2):
    retriever, _ = stack
    (pool,), errors = retriever.pools([query])
    assert not errors and pool
    order = list(dict.fromkeys(c.doc_id for c in pool))
    return set(order[:n])


@pytest.mark.parametrize("query", ["triệu chứng sỏi thận", "kidney stones symptoms", "肾结石症状"])
def test_kidney_query_finds_both_languages_of_the_concept(stack, query):
    assert _top_docs(stack, query) == KIDNEY


@pytest.mark.parametrize("query", ["lịch thi đấu giải bóng đá", "football league schedule", "足球联赛赛程"])
def test_football_query_finds_both_languages_of_the_concept(stack, query):
    assert _top_docs(stack, query) == FOOTBALL


def test_pool_scores_are_rerank_scores_in_unit_range(stack):
    retriever, _ = stack
    (pool,), _ = retriever.pools(["triệu chứng sỏi thận"])
    assert all(0.0 <= c.score <= 1.0 for c in pool) and [c.score for c in pool] == sorted((c.score for c in pool), reverse=True)


def test_selection_puts_the_right_concept_first(stack):
    from retrieval.select import select
    retriever, s = stack
    (pool,), _ = retriever.pools(["kidney stones symptoms"])
    assert select(pool, s.retrieve.select).doc_ids[0] in KIDNEY


def test_multi_intent_query_reaches_both_topics(stack):
    assert _top_docs(stack, "Triệu chứng sỏi thận là gì? Lịch thi đấu giải bóng đá ra sao?", n=4) == KIDNEY | FOOTBALL