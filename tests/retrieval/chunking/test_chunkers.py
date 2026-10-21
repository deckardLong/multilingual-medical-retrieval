import pytest
from common.schema import Chunk
from retrieval.chunking import build_chunker
from retrieval.chunking.validate import validate_doc_chunks, coverage
from factories import make_doc, article, paragraph


def test_registry_unknown_method(settings, counter):
    bad = settings.chunk.model_copy(update=dict(method="nope"))
    with pytest.raises(KeyError):
        build_chunker(bad, counter, "t")


def test_structure_verbatim_and_full_coverage(chunker):
    doc = article(sections=5, paras=4, words=60)
    cs = chunker.split(doc)
    assert len(cs) > 3
    assert validate_doc_chunks(doc, cs) == []
    assert coverage(doc, cs) == 1.0


def test_structure_headings_and_ctx(chunker):
    cs = chunker.split(article(sections=3))
    heads = {c.heading for c in cs}
    assert any(h.startswith("Mục số") for h in heads)
    assert all(c.ctx.startswith("Tiêu đề bài viết") for c in cs)


def test_chunk_ids_unique_and_stable(chunker):
    doc = article()
    a, b = chunker.split(doc), chunker.split(doc)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert len({c.chunk_id for c in a}) == len(a)
    assert all(c.chunk_id.startswith(doc.uid + "#") and c.uid == doc.uid for c in a)


def test_parent_contains_child_and_within_budget(chunker, settings):
    doc = article(sections=4, paras=5)
    for c in chunker.split(doc):
        assert c.p_start <= c.start and c.end <= c.p_end
        assert chunker.count.count(doc.text[c.p_start:c.p_end]) <= settings.chunk.parent.max_tokens + 50


def test_long_paragraph_is_split_and_bounded(chunker, settings):
    doc = make_doc("Tiêu đề\n" + paragraph(1, 1500) + "\n")
    cs = chunker.split(doc)
    assert len(cs) > 1 and validate_doc_chunks(doc, cs) == []
    assert max(c.n_tokens for c in cs) <= settings.chunk.max_tokens + 5


@pytest.mark.parametrize("text", ["", "\n\n", "Chỉ có tiêu đề", "Tiêu đề\n\n\n"])
def test_empty_or_title_only(chunker, text):
    assert chunker.split(make_doc(text)) == []


def test_short_doc_single_chunk(chunker):
    doc = make_doc("Tiêu đề\nMột đoạn ngắn.\n")
    cs = chunker.split(doc)
    assert len(cs) == 1 and cs[0].text == "Một đoạn ngắn."


def test_chinese_doc(chunker):
    body = "\n".join("这是一个关于疾病治疗的段落，内容包括症状和处理方法。" * 8 for _ in range(6))
    doc = make_doc("标题\n" + body + "\n", title="标题", uid="zh:9", lang="zh")
    cs = chunker.split(doc)
    assert cs and validate_doc_chunks(doc, cs) == [] and coverage(doc, cs) == 1.0


def test_parent_disabled(settings, counter):
    cfg = settings.chunk.model_copy(update=dict(parent=settings.chunk.parent.model_copy(update=dict(enabled=False))))
    ch = build_chunker(cfg, counter, "t")
    for c in ch.split(article()):
        assert (c.p_start, c.p_end) == (c.start, c.end)


def test_contextual_prefix_off(settings, counter):
    ch = build_chunker(settings.chunk.model_copy(update=dict(contextual_prefix=False)), counter, "t")
    assert all(c.ctx == "" for c in ch.split(article()))


def test_recursive_empty_doc(settings, counter):
    ch = build_chunker(settings.chunk.model_copy(update=dict(method="recursive")), counter, "t")
    assert ch.split(make_doc("")) == []


def test_recursive_baseline(settings, counter):
    ch = build_chunker(settings.chunk.model_copy(update=dict(method="recursive")), counter, "t")
    doc = article(sections=4, paras=4, words=60)
    cs = ch.split(doc)
    assert cs and validate_doc_chunks(doc, cs) == []