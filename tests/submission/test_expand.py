from common.schema import Candidate
from retrieval.results import QueryResult
from submission import build_item
from submission.expand import Expander, sentence_spans, widen
from submission.settings import BuildCfg

DOC = "Câu một có năm từ. Câu hai cũng năm từ. Câu ba thì có sáu từ. Câu bốn ngắn."


def cand(uid, text, start, chunk=0):
    return Candidate(chunk_id=f"{uid}#{chunk}", uid=uid, doc_id=uid.split(":")[1], start=start, end=start + len(text),
                     p_start=start, p_end=start + len(text), score=1.0, text=text)


def span_of(s):
    i = DOC.index(s)
    return i, i + len(s)


def test_widen_adds_neighbour_sentences_up_to_target_and_never_splits_a_sentence():
    a, b = widen(sentence_spans(DOC), *span_of("Câu hai cũng năm từ."), target=11)
    assert DOC[a:b] == "Câu hai cũng năm từ. Câu ba thì có sáu từ."


def test_widen_grows_backwards_when_the_next_sentence_does_not_fit():
    a, b = widen(sentence_spans(DOC), *span_of("Câu hai cũng năm từ."), target=10)
    assert DOC[a:b] == "Câu một có năm từ. Câu hai cũng năm từ."


def test_widen_never_shrinks_a_chunk_longer_than_target():
    s, e = span_of("Câu hai cũng năm từ. Câu ba thì có sáu từ.")
    assert widen(sentence_spans(DOC), s, e, target=3) == (s, e)


def test_expanded_build_is_verbatim_and_skips_chunks_already_inside_a_window():
    one, two = "Câu hai cũng năm từ.", "Câu ba thì có sáu từ."
    r = QueryResult(qid=1, query="q", candidates=[cand("vi:9", one, DOC.index(one)), cand("vi:9", two, DOC.index(two), 1)])
    it = build_item(r, BuildCfg(max_docs=None, max_chunks=None), Expander({"vi:9": DOC}, 11))
    assert [c.chunk_text for c in it.relevant_chunks] == ["Câu hai cũng năm từ. Câu ba thì có sáu từ."]
    assert all(c.chunk_text in DOC for c in it.relevant_chunks)


def test_doc_without_text_keeps_its_original_chunk():
    r = QueryResult(qid=1, query="q", candidates=[cand("vi:5", "abc", 0)])
    it = build_item(r, BuildCfg(max_docs=None, max_chunks=None), Expander({}, 50))
    assert [c.chunk_text for c in it.relevant_chunks] == ["abc"]
