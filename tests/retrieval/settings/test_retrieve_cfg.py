import pytest
from pydantic import ValidationError
from retrieval.settings.checks import check_compat
from retrieval.settings.retrieve import DecomposeCfg, SearchCfg, SelectCfg


def _d(cfg, **kw):
    return {**cfg.model_dump(), **kw}


# ---- search -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("field", ["k_dense", "k_sparse", "k_fuse", "k_pool", "rrf_k", "hnsw_ef"])
def test_search_sizes_must_be_positive(settings, field):
    with pytest.raises(ValidationError):
        SearchCfg(**_d(settings.retrieve.search, **{field: 0}))


def test_oversampling_must_be_at_least_one(settings):
    with pytest.raises(ValidationError):
        SearchCfg(**_d(settings.retrieve.search, oversampling=0.99))
    assert SearchCfg(**_d(settings.retrieve.search, oversampling=1.0)).oversampling == 1.0


def test_search_langs_may_be_null_or_a_list(settings):
    assert SearchCfg(**_d(settings.retrieve.search, langs=None)).langs is None
    assert SearchCfg(**_d(settings.retrieve.search, langs=["vi", "zh"])).langs == ["vi", "zh"]


# ---- select -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("kw", [dict(max_docs=0), dict(chunks_per_doc=0), dict(min_score=-0.01), dict(min_score=1.01),
                                dict(rel_drop=0.0), dict(rel_drop=-0.5), dict(rel_drop=1.01)])
def test_select_rejects_out_of_range_values(settings, kw):
    with pytest.raises(ValidationError):
        SelectCfg(**_d(settings.retrieve.select, **kw))


@pytest.mark.parametrize("kw", [dict(min_score=0.0), dict(min_score=1.0), dict(rel_drop=1.0), dict(min_score=None, rel_drop=None)])
def test_select_accepts_boundary_values(settings, kw):
    SelectCfg(**_d(settings.retrieve.select, **kw))


# ---- decompose --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("kw", [dict(max_subqueries=0), dict(min_part_tokens=0), dict(mode="llm")])
def test_decompose_rejects_bad_values(settings, kw):
    with pytest.raises(ValidationError):
        DecomposeCfg(**_d(settings.retrieve.decompose, **kw))


def test_unknown_fields_are_rejected_everywhere(settings):
    for cfg, cls in [(settings.retrieve.search, SearchCfg), (settings.retrieve.select, SelectCfg),
                     (settings.retrieve.decompose, DecomposeCfg)]:
        with pytest.raises(ValidationError):
            cls(**_d(cfg, typo_field=1))


# ---- kiểm tra chéo ----------------------------------------------------------------------------------------------

def test_k_fuse_cannot_exceed_k_dense_plus_k_sparse(settings):
    s = settings
    bad = s.retrieve.model_copy(update=dict(search=s.retrieve.search.model_copy(update=dict(k_dense=10, k_sparse=10, k_fuse=21))))
    with pytest.raises(ValueError, match="k_fuse"):
        check_compat(s.chunk, s.embed, s.rerank, bad)
    ok = s.retrieve.model_copy(update=dict(search=s.retrieve.search.model_copy(update=dict(k_dense=10, k_sparse=10, k_fuse=20))))
    check_compat(s.chunk, s.embed, s.rerank, ok)


def test_k_pool_must_cover_max_docs_boundary(settings):
    s = settings
    def with_(pool): return s.retrieve.model_copy(update=dict(search=s.retrieve.search.model_copy(update=dict(k_pool=pool))))
    check_compat(s.chunk, s.embed, s.rerank, with_(s.retrieve.select.max_docs))              # bằng nhau: hợp lệ
    with pytest.raises(ValueError, match="k_pool"):
        check_compat(s.chunk, s.embed, s.rerank, with_(s.retrieve.select.max_docs - 1))