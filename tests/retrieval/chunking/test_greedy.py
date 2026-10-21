from retrieval.chunking.split import GreedySplitter
from retrieval.chunking.tokens import ApproxTokenCounter


def _g(settings, size=30):
    return GreedySplitter(settings.chunk.recursive.model_copy(update=dict(chunk_size=size)), ApproxTokenCounter())


def _assert_exact_cover(text, spans):
    assert spans[0][0] == len(text) - len(text.lstrip()) and spans[-1][1] == len(text.rstrip())
    for (_, e0), (s1, _) in zip(spans, spans[1:]):
        assert s1 > 0 and not text[e0:s1].strip()               # chỉ có khoảng trắng giữa hai mảnh liền kề
    assert all(text[a:b] == text[a:b].strip() for a, b in spans)


def test_words_cover_exactly_and_respect_size(settings):
    text = " ".join(f"từ{i}" for i in range(300))
    spans = _g(settings).spans(text, 0, len(text))
    assert len(spans) > 5
    _assert_exact_cover(text, spans)
    assert all(ApproxTokenCounter().count(text[a:b]) <= 30 for a, b in spans)


def test_unbroken_chinese_split_by_character(settings):
    text = "糖尿病的症状包括口渴和多尿" * 40
    spans = _g(settings).spans(text, 0, len(text))
    assert len(spans) > 5 and "".join(text[a:b] for a, b in spans) == text
    assert all(ApproxTokenCounter().count(text[a:b]) <= 30 for a, b in spans)


def test_subrange_and_empty(settings):
    text = "XX " + " ".join(f"w{i}" for i in range(100)) + " YY"
    spans = _g(settings).spans(text, 3, len(text) - 3)
    assert spans[0][0] == 3 and spans[-1][1] == len(text) - 3
    assert _g(settings).spans("   ", 0, 3) == []