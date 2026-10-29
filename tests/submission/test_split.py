import re
from factories import cand_of
from retrieval.results import QueryResult
from submission import build_item
from submission.settings import BuildCfg
from submission.split import split_text

TEXT = ("Viêm dạ dày là tình trạng niêm mạc dạ dày bị tổn thương. Nguyên nhân thường do vi khuẩn Hp hoặc thuốc giảm đau. "
        "Triệu chứng gồm đau thượng vị, ợ chua và buồn nôn sau khi ăn.\nĐiều trị cần dùng thuốc theo chỉ định của bác sĩ, "
        "kết hợp ăn uống điều độ và tránh rượu bia.")


def words(s):
    return len(s.split())


def test_pieces_are_verbatim_substrings_in_order_and_cover_every_word():
    parts = split_text(TEXT, 15)
    pos = 0
    for p in parts:
        i = TEXT.index(p, pos)
        assert i >= pos
        pos = i + len(p)
    assert " ".join(" ".join(parts).split()) == " ".join(TEXT.split())


def test_pieces_respect_the_limit_and_break_at_sentences():
    parts = split_text(TEXT, 15)
    assert all(words(p) <= 15 for p in parts) and len(parts) >= 3
    assert parts[0].endswith("tổn thương.")


def test_a_sentence_longer_than_the_limit_is_cut_hard():
    long = " ".join(f"từ{i}" for i in range(25)) + "."
    assert [words(p) for p in split_text(long, 10)] == [10, 10, 5]


def test_tiny_tail_is_merged_into_the_previous_piece():
    text = " ".join(f"a{i}" for i in range(10)) + ". Hết."
    assert split_text(text, 10) == [text]


def test_chinese_is_counted_per_character():
    zh = "糖尿病的症状包括口渴和多尿。糖尿病的治疗方法包括胰岛素和饮食控制。"
    parts = split_text(zh, 16)
    assert parts == ["糖尿病的症状包括口渴和多尿。", "糖尿病的治疗方法包括胰岛素和饮食控制。"]


def _cfg(**kw):
    return BuildCfg(**{"max_docs": None, "max_chunks": None, **kw})


def test_build_submits_the_full_chunk_then_its_pieces():
    r = QueryResult(qid=1, query="q", candidates=[cand_of("vi:1", 0, TEXT)])
    texts = [c.chunk_text for c in build_item(r, _cfg(split_max_words=15)).relevant_chunks]
    assert texts[0] == TEXT and texts[1:] == split_text(TEXT, 15)


def test_build_can_drop_the_full_chunk_and_short_chunks_stay_whole():
    r = QueryResult(qid=1, query="q", candidates=[cand_of("vi:1", 0, TEXT), cand_of("vi:2", 0, "Ngắn gọn thôi.")])
    item = build_item(r, _cfg(split_max_words=15, keep_full_chunk=False))
    texts = [c.chunk_text for c in item.relevant_chunks]
    assert TEXT not in texts and texts[-1] == "Ngắn gọn thôi." and [c.doc_id for c in item.relevant_chunks][-1] == "2"


def test_without_split_nothing_changes():
    r = QueryResult(qid=1, query="q", candidates=[cand_of("vi:1", 0, TEXT)])
    assert [c.chunk_text for c in build_item(r, _cfg()).relevant_chunks] == [TEXT]
