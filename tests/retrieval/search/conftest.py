import itertools
import json
from types import SimpleNamespace
import pytest
from qdrant_client import QdrantClient
from common.schema import Doc
from retrieval.embedding import build_embedder
from retrieval.index import Manifest
from retrieval.pipeline import run_cycle
from retrieval.rerank import build_reranker

TOPICS = {
    "vi:1": ("Bệnh tiểu đường", "Triệu chứng của bệnh tiểu đường gồm khát nhiều và tiểu nhiều.\nĐiều trị tiểu đường bằng insulin và chế độ ăn."),
    "vi:2": ("Cao huyết áp", "Cao huyết áp gây đau đầu và chóng mặt.\nThuốc hạ huyết áp giúp kiểm soát huyết áp."),
    "vi:3": ("Hen suyễn", "Hen suyễn gây khó thở và ho về đêm.\nThuốc giãn phế quản dùng cho người hen suyễn."),
    "zh:4": ("糖尿病", "糖尿病的症状包括口渴和多尿。\n糖尿病的治疗方法包括胰岛素。"),
}


def _doc(uid, title, body):
    lang = uid.split(":")[0]
    return Doc(uid=uid, doc_id=uid.split(":")[1], lang=lang, url="u", title=title, text=f"{title}\n{body}\n")


@pytest.fixture
def world(tmp_path, settings, chunker, fake_cfg):
    """Kho nhỏ 4 bài (3 vi + 1 zh) đã chunk → embed (giả) → upsert vào Qdrant trong bộ nhớ."""
    emb_cfg = fake_cfg.model_copy(update=dict(use_sparse=True))
    corpus = tmp_path / "corpus"; corpus.mkdir()
    (corpus / "s.jsonl").write_text("\n".join(json.dumps(_doc(u, *v).model_dump(), ensure_ascii=False)
                                              for u, v in TOPICS.items()) + "\n", encoding="utf-8")
    s = SimpleNamespace(env=SimpleNamespace(r2ai_corpus_dir=corpus), chunks_dir=tmp_path / "c", vectors_dir=tmp_path / "v",
                        collection="t", index=settings.index, embed=emb_cfg, retrieve=settings.retrieve,
                        rerank=settings.rerank.model_copy(update=dict(backend="fake")))
    client, emb = QdrantClient(":memory:"), build_embedder(emb_cfg)
    run_cycle(s, client, Manifest(tmp_path / "m.jsonl"), lambda: chunker, lambda: emb)
    return s, client, emb, build_reranker(s.rerank)


@pytest.fixture
def run_world(world):
    """world + run_id/run_card của riêng bài test: run_id duy nhất mỗi lần gọi (không phụ thuộc đồng hồ),
    run_card phản ánh retrieve/rerank HIỆN TẠI của `s` (test có thể đổi select rồi chạy lại)."""
    s, client, emb, rr = world
    counter = itertools.count(1)
    s.run_id = lambda: f"run{next(counter)}"
    s.run_card = lambda: {"collection": s.collection, "retrieve": s.retrieve.model_dump(mode="json"),
                          "rerank": s.rerank.model_dump(mode="json")}
    return s, client, emb, rr


@pytest.fixture
def docs():
    """uid → Doc gốc của kho thử; dùng để kiểm tra chunk_text/offset trả về khớp với văn bản gốc."""
    return {u: _doc(u, *v) for u, v in TOPICS.items()}