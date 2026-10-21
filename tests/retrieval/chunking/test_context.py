from retrieval.chunking.context import make_ctx, embed_text


def test_ctx_title_and_heading():
    assert make_ctx(True, " Bệnh X ", " Triệu chứng ") == "Bệnh X | Triệu chứng"


def test_ctx_no_heading_or_same_as_title():
    assert make_ctx(True, "Bệnh X", "") == "Bệnh X"
    assert make_ctx(True, "Bệnh X", "Bệnh X") == "Bệnh X"


def test_ctx_disabled():
    assert make_ctx(False, "t", "h") == ""


def test_embed_text():
    assert embed_text("a | b", "nội dung") == "a | b\nnội dung"
    assert embed_text("", "nội dung") == "nội dung"