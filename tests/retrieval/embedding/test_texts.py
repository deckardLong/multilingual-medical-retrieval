from retrieval.embedding.texts import chunk_texts


def test_prefix_is_prepended_only_when_ctx_present():
    out = chunk_texts(["Tiêu đề | Mục A", ""], ["nội dung 1", "nội dung 2"])
    assert out == ["Tiêu đề | Mục A\nnội dung 1", "nội dung 2"]


def test_does_not_modify_chunk_text():
    assert chunk_texts(["c"], ["  giữ nguyên khoảng trắng  "])[0].endswith("  giữ nguyên khoảng trắng  ")