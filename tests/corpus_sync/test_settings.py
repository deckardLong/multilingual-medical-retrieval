import pytest
from pydantic import ValidationError
from corpus_sync import SyncCfg


def _d(cfg, **kw):
    return {**cfg.model_dump(), **kw}


def test_shipped_defaults_point_at_the_real_hf_dataset(sync_cfg):
    assert sync_cfg.repo_id == "ai-guru-medical-retrieval/multilingual-medical-retrieval-corpus"
    assert sync_cfg.repo_type == "dataset" and sync_cfg.revision == "main"
    assert any("viz/docs" in p for p in sync_cfg.allow_patterns)
    assert any(p.endswith("query.parquet") for p in sync_cfg.allow_patterns)
    assert any("links_corpus.parquet" in p for p in sync_cfg.allow_patterns)


@pytest.mark.parametrize("field", ["repo_id", "revision"])
def test_blank_strings_are_rejected(sync_cfg, field):
    with pytest.raises(ValidationError):
        SyncCfg(**_d(sync_cfg, **{field: "  "}))


def test_empty_allow_patterns_is_rejected(sync_cfg):
    with pytest.raises(ValidationError):
        SyncCfg(**_d(sync_cfg, allow_patterns=[]))


@pytest.mark.parametrize("n", [0, -1])
def test_max_workers_must_be_positive(sync_cfg, n):
    with pytest.raises(ValidationError):
        SyncCfg(**_d(sync_cfg, max_workers=n))


def test_unknown_field_is_rejected(sync_cfg):
    with pytest.raises(ValidationError):
        SyncCfg(**_d(sync_cfg, extra_field=1))