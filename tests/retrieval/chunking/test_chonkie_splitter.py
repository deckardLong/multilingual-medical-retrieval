import pytest
pytest.importorskip("chonkie")
from retrieval.chunking.split.chonkie_splitter import ChonkieSplitter
from retrieval.chunking.tokens import ApproxTokenCounter
from factories import paragraph


def _sp(settings, size=60):
    cfg = settings.chunk.recursive.model_copy(update=dict(chunk_size=size))
    return ChonkieSplitter(cfg, ApproxTokenCounter())


def test_spans_verbatim_in_range_and_cover(settings):
    text = "\n".join(paragraph(i, 30) for i in range(6))
    spans = _sp(settings).spans(text, 0, len(text))
    assert len(spans) > 1
    assert all(0 <= a < b <= len(text) for a, b in spans)
    assert "".join(text[a:b] for a, b in spans) == text          # Chonkie không mất ký tự nào


def test_offsets_shifted_by_start(settings):
    text = "XX\n" + "\n".join(paragraph(i, 30) for i in range(4)) + "\nYY"
    spans = _sp(settings).spans(text, 3, len(text) - 3)
    assert spans[0][0] == 3 and spans[-1][1] == len(text) - 3


def test_unbroken_text_falls_back_instead_of_crashing(settings):
    text = " ".join(f"w{i}" for i in range(400))                  # Chonkie + hàm đếm token: NotImplementedError
    spans = _sp(settings).spans(text, 0, len(text))
    assert spans and spans[0][0] == 0 and spans[-1][1] == len(text)