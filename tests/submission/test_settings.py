import pytest
import yaml
from pydantic import ValidationError
from common.config import Env, ROOT, load_cfg
from submission import SubmitCfg


def _d(cfg, **kw):
    return {**cfg.model_dump(mode="json"), **kw}


def test_shipped_defaults_describe_the_btc_format(submit_cfg):
    assert submit_cfg.json_name.endswith(".json") and submit_cfg.check.max_chunk_tokens == 1024
    assert submit_cfg.build.max_docs is None and submit_cfg.build.max_chunks is None


def test_shipped_yaml_has_no_leftover_todo():
    assert "TODO" not in (ROOT / "configs" / "submit.yaml").read_text("utf-8")


@pytest.mark.parametrize("name", ["a/b.json", "dir\\b.json", "sub.txt", "sub.zip", "sub"])
def test_json_name_must_be_a_bare_json_file_name(submit_cfg, name):
    with pytest.raises(ValidationError):
        SubmitCfg(**_d(submit_cfg, json_name=name))


@pytest.mark.parametrize("build", [dict(max_docs=0, max_chunks=None), dict(max_docs=None, max_chunks=0), dict(max_docs=-3, max_chunks=None)])
def test_limits_must_be_positive_or_null(submit_cfg, build):
    with pytest.raises(ValidationError):
        SubmitCfg(**_d(submit_cfg, build=build))


def test_positive_limits_are_accepted(submit_cfg):
    assert SubmitCfg(**_d(submit_cfg, build=dict(max_docs=5, max_chunks=12))).build.max_docs == 5


def test_chunk_token_limit_must_be_positive(submit_cfg):
    with pytest.raises(ValidationError):
        SubmitCfg(**_d(submit_cfg, check=dict(btc_ids_path=None, max_chunk_tokens=0, token_counter="approx")))


def test_unknown_keys_are_rejected(submit_cfg):
    with pytest.raises(ValidationError):
        SubmitCfg(**_d(submit_cfg, k_docs=10))                          # khóa cũ trong bản nháp trước


def test_experiment_overlay_can_change_submit_settings(cfg_dir, monkeypatch):
    (cfg_dir / "exp" / "wide").mkdir(parents=True)
    (cfg_dir / "exp" / "wide" / "submit.yaml").write_text(yaml.safe_dump({"build": {"max_docs": 20}}))
    monkeypatch.setenv("R2AI_EXPERIMENT", "wide")
    assert load_cfg("submit", SubmitCfg, Env()).build.max_docs == 20