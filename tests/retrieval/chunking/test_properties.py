"""300 bài ngẫu nhiên (seed cố định): mọi chunk PHẢI nguyên văn, phủ đủ, không vượt giới hạn."""
import random
import pytest
from retrieval.chunking.validate import validate_doc_chunks, coverage
from factories import make_doc

VI = "bệnh triệu chứng điều trị thuốc người huyết áp đường gan phổi tim xét nghiệm chẩn đoán".split()
ZH = list("糖尿病高血压症状治疗药物检查诊断预防饮食运动")


def _sentence(rng, zh):
    if zh:
        return "".join(rng.choice(ZH) for _ in range(rng.randint(5, 60))) + rng.choice(["。", "，", ""])
    return " ".join(rng.choice(VI) for _ in range(rng.randint(3, 50))) + rng.choice([".", "?", ",", ""])


def _doc(seed):
    rng = random.Random(seed)
    zh = rng.random() < 0.3
    lines = ["Tiêu đề bài " + str(seed)]
    for _ in range(rng.randint(0, 25)):
        r = rng.random()
        if r < 0.15:
            lines.append("")                                         # dòng trống
        elif r < 0.3:
            lines.append(" ".join(rng.choice(VI) for _ in range(rng.randint(1, 5))))      # giống heading
        elif r < 0.35:
            lines.append(_sentence(rng, zh) * rng.randint(10, 40))   # đoạn rất dài, lặp lại
        else:
            lines.append(_sentence(rng, zh))
    sep = rng.choice(["\n", "\n", "\r\n", "\n\n"])
    return make_doc(sep.join(lines) + rng.choice(["", "\n"]), uid=f"vi:{seed}")


@pytest.mark.parametrize("method", ["structure", "recursive"])
def test_invariants_on_random_docs(settings, counter, method):
    from retrieval.chunking import build_chunker
    ch = build_chunker(settings.chunk.model_copy(update=dict(method=method)), counter, "t")
    limit = settings.chunk.max_tokens
    for seed in range(300):
        doc = _doc(seed)
        cs = ch.split(doc)
        assert validate_doc_chunks(doc, cs) == [], f"seed={seed}"
        assert coverage(doc, cs) >= 0.999, f"seed={seed}"
        assert all(c.n_tokens <= limit + 5 for c in cs), f"seed={seed}"
        assert [c.chunk_id for c in cs] == [f"{doc.uid}#{i}" for i in range(len(cs))]