import os, sys, types
import pytest

class StubTok:
    def encode(self, text, add_special_tokens):
        assert add_special_tokens is False
        return text.split()

    def __call__(self, texts, add_special_tokens, return_attention_mask, return_token_type_ids):
        return {"input_ids": [t.split() for t in texts]}

@pytest.fixture
def counter(monkeypatch):
    mod = types.ModuleType("transformers")
    setattr(mod, "AutoTokenizer", types.SimpleNamespace(from_pretrained=lambda name, **kw: StubTok()))
    monkeypatch.setitem(sys.modules, "transformers", mod)
    from retrieval.chunking import build_counter
    return build_counter("BAAI/bge-m3")


def test_count_and_count_many_agree(counter):
    xs = ["a b c", "", "d e"]
    assert counter.count("a b c") == 3
    assert counter.count_many(xs) == [3, 0, 2] == [counter.count(x) for x in xs]


def test_count_many_empty_list(counter):
    assert counter.count_many([]) == []


@pytest.mark.gpu
@pytest.mark.skipif(os.environ.get("R2AI_TEST_REAL_MODEL") != "1", reason="cần tokenizer thật (tải từ HF)")
def test_real_bge_m3_tokenizer_keeps_chunks_within_limits(settings):
    """Điều test xấp xỉ không làm được: với tokenizer THẬT, chunk có vượt hard_tokens/embed.max_length không."""
    from retrieval.chunking import build_chunker, build_counter
    from factories import make_doc
    real = build_counter(settings.chunk.tokenizer)
    ch = build_chunker(settings.chunk, real, "t")
    vi = "Bệnh tiểu đường type 2 là bệnh mạn tính ảnh hưởng đến cách cơ thể chuyển hóa đường trong máu. " * 12
    zh = "糖尿病是一种慢性代谢性疾病，需要长期管理血糖水平并定期复查。" * 20
    for doc in (make_doc("Tiêu đề\n" + vi + "\nMục hai\n" + vi), make_doc("标题\n" + zh + "\n小节\n" + zh, uid="zh:1", lang="zh")):
        for c in ch.split(doc):
            assert c.n_tokens == real.count(c.text)
            assert c.n_tokens + settings.chunk.ctx_margin_tokens <= settings.embed.max_length