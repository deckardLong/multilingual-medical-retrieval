from retrieval.chunking.split import OversizeSplitter
from retrieval.chunking.tokens import ApproxTokenCounter
from factories import paragraph


def _sp(settings, size=60, overlap=10):
    cfg = settings.chunk.recursive.model_copy(update=dict(chunk_size=size, chunk_overlap=overlap))
    return OversizeSplitter(cfg, ApproxTokenCounter())


def test_spans_are_verbatim_and_in_range(settings):
    text = "\n".join(paragraph(i, 30) for i in range(6))
    spans = _sp(settings).spans(text, 0, len(text))
    assert len(spans) > 1
    for a, b in spans:
        assert 0 <= a < b <= len(text) and text[a:b].strip() == text[a:b]


def test_spans_respect_subrange(settings):
    text = "XX\n" + "\n".join(paragraph(i, 30) for i in range(4)) + "\nYY"
    spans = _sp(settings).spans(text, 3, len(text) - 3)
    assert spans[0][0] >= 3 and spans[-1][1] <= len(text) - 3


def test_spans_advance(settings):
    text = " ".join(f"w{i}" for i in range(300))
    spans = _sp(settings, 40, 5).spans(text, 0, len(text))
    starts = [a for a, _ in spans]
    assert starts == sorted(starts) and len(set(starts)) == len(starts)


def test_unlocatable_piece_falls_back_to_greedy(settings):
    sp = _sp(settings)
    sp.sp.split_text = lambda text: ["không có trong văn bản"]
    text = " ".join(f"w{i}" for i in range(200))
    spans = sp.spans(text, 0, len(text))
    assert spans and spans[0][0] == 0 and spans[-1][1] == len(text)


def test_repeated_text_is_fully_covered_regression(settings):
    """Lỗi từng gặp: nội dung lặp lại làm `find` định vị mảnh sau về chỗ cũ → mất cả vùng văn bản."""
    text = ("triệu chứng của bệnh tiểu đường gồm khát nhiều. " * 80).strip()
    spans = _sp(settings, size=50, overlap=10).spans(text, 0, len(text))
    covered = bytearray(len(text))
    for a, b in spans:
        assert text[a:b] == text[a:b].strip()
        covered[a:b] = b"\x01" * (b - a)
    assert all(covered[i] or text[i].isspace() for i in range(len(text)))          # không còn khoảng hở
    assert [a for a, _ in spans] == sorted(a for a, _ in spans)


def test_chunks_never_start_before_previous_start(settings):
    text = " ".join(["lặp lại"] * 400)
    starts = [a for a, _ in _sp(settings, size=30, overlap=5).spans(text, 0, len(text))]
    assert all(y > x for x, y in zip(starts, starts[1:]))


def test_primary_path_used_for_normal_text(settings):
    """Văn bản bình thường: kết quả của LangChain được giữ (có overlap), không phải phương án cuối."""
    text = "\n".join(paragraph(i, 40) for i in range(8))
    sp = _sp(settings, size=60, overlap=10)
    assert sp.spans(text, 0, len(text)) == sp._locate(text, 0, len(text))