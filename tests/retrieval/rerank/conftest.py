import pytest


@pytest.fixture
def rcfg(settings):
    return settings.rerank.model_copy(update=dict(backend="fake"))