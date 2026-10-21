import pytest
from common.config import Env, load_cfg
from submission import SubmitCfg
from submission.settings import BuildCfg


class WordCounter:
    """Bộ đếm token giả: mỗi từ cách nhau bằng khoảng trắng là một token (dễ tính nhẩm trong test)."""
    def count(self, text): return len(text.split())
    def count_many(self, texts): return [self.count(t) for t in texts]


@pytest.fixture
def submit_cfg():
    return load_cfg("submit", SubmitCfg, Env())


@pytest.fixture
def build_cfg():
    return BuildCfg(max_docs=None, max_chunks=None)


@pytest.fixture
def words():
    return WordCounter()