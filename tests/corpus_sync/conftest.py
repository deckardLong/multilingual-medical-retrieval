import pytest
from common.config import Env, load_cfg
from corpus_sync import SyncCfg


@pytest.fixture
def sync_cfg():
    return load_cfg("corpus_sync", SyncCfg, Env())