import pytest
from pydantic import ValidationError
from common.config import Env
from retrieval.settings import load_all
from retrieval.settings.checks import check_compat
from retrieval.settings.rerank import RerankCfg


def _d(settings, **kw):
    return {**settings.rerank.model_dump(), **kw}


@pytest.mark.parametrize("field", ["batch_size", "max_length"])
@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_sizes_rejected(settings, field, value):
    with pytest.raises(ValidationError):
        RerankCfg(**_d(settings, **{field: value}))


@pytest.mark.parametrize("kw", [dict(backend="qwen3"), dict(query_mode="sum"), dict(unknown_field=1)])
def test_unknown_values_and_extra_fields_rejected(settings, kw):
    with pytest.raises(ValidationError):
        RerankCfg(**_d(settings, **kw))


def test_config_is_frozen(settings):
    with pytest.raises(Exception):
        settings.rerank.batch_size = 1


def test_rerank_max_length_must_fit_chunk_plus_query(settings):
    s = settings
    with pytest.raises(ValueError, match="rerank.max_length"):
        check_compat(s.chunk, s.embed, s.rerank.model_copy(update=dict(max_length=128)), s.retrieve)


def test_small_rerank_max_length_is_fine_when_rerank_disabled(settings):
    s = settings
    check_compat(s.chunk, s.embed, s.rerank.model_copy(update=dict(max_length=128, enabled=False)), s.retrieve)


def test_min_score_requires_rerank(settings):
    s = settings
    retrieve = s.retrieve.model_copy(update=dict(select=s.retrieve.select.model_copy(update=dict(min_score=0.3))))
    check_compat(s.chunk, s.embed, s.rerank, retrieve)                                    # rerank bật: hợp lệ
    with pytest.raises(ValueError, match="min_score"):
        check_compat(s.chunk, s.embed, s.rerank.model_copy(update=dict(enabled=False)), retrieve)


def test_rerank_change_keeps_every_build_hash_but_changes_run_id(cfg_dir):
    base = load_all(Env())
    p = cfg_dir / "rerank.yaml"
    p.write_text(p.read_text().replace("batch_size: 32", "batch_size: 16").replace("max_length: 512", "max_length: 640"))
    new = load_all(Env())
    assert (new.h_chunk, new.h_embed, new.h_index) == (base.h_chunk, base.h_embed, base.h_index)
    assert new.collection == base.collection
    assert new.run_id()[-4:] != base.run_id()[-4:]                    # 4 ký tự cuối = hash cấu hình truy vấn