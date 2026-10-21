import pytest
from pydantic import ValidationError
from retrieval.settings.embed import EmbedCfg


def test_query_len_not_above_doc_len(settings):
    d = settings.embed.model_dump(); d["query_max_length"] = d["max_length"] + 1
    with pytest.raises(ValidationError):
        EmbedCfg(**d)


def test_unknown_backend_rejected(settings):
    d = settings.embed.model_dump(); d["backend"] = "qwen3"
    with pytest.raises(ValidationError):
        EmbedCfg(**d)


def test_runtime_fields_not_in_hash(settings):
    a = settings.embed.fingerprint()
    assert a == settings.embed.model_copy(update=dict(batch_size=1, slice_size=1, query_max_length=8)).fingerprint()
    assert a != settings.embed.model_copy(update=dict(max_length=256)).fingerprint()


@pytest.mark.parametrize("field,value", [("model", "other/model"), ("fp16", False), ("dim", 512),
                                         ("use_sparse", False), ("version", 2), ("name", "bge-m3-b")])
def test_fields_that_change_vectors_change_the_hash(settings, field, value):
    assert settings.embed.fingerprint() != settings.embed.model_copy(update={field: value}).fingerprint()


def test_embed_tag_carries_the_chained_hash(settings):
    """Thư mục vectors mang h_embed (hash embed + hash chunk): đổi cách chunk cũng buộc embed lại."""
    assert settings.embed_tag == f"{settings.embed.ver}-{settings.h_embed[:6]}"
    assert settings.h_embed != settings.embed.fingerprint()