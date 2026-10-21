import shutil
import pytest
from common.config import ROOT, Env
from retrieval.settings import load_all
from retrieval.chunking import build_chunker, build_counter


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("R2AI_EXPERIMENT", "R2AI_CONFIG_DIR", "R2AI_CORPUS_DIR", "R2AI_DERIVED_DIR", "R2AI_STATE_DIR"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def settings():
    return load_all(Env())


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    """Bản sao configs/ trong thư mục tạm: test sửa thoải mái mà không đụng repo."""
    dst = tmp_path / "configs"
    shutil.copytree(ROOT / "configs", dst)
    monkeypatch.setenv("R2AI_CONFIG_DIR", str(dst))
    return dst


@pytest.fixture(scope="session")
def counter():
    return build_counter("approx")


@pytest.fixture
def chunker(settings, counter):
    return build_chunker(settings.chunk, counter, settings.chunk_tag)


@pytest.fixture
def fake_cfg(settings):
    """Cấu hình embed giả: vector nhỏ để test nhanh."""
    return settings.embed.model_copy(update=dict(backend="fake", dim=64, max_length=64,
                                                 query_max_length=16, slice_size=8, batch_size=4))