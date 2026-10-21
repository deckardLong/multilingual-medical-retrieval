"""Cấu hình đi kèm repo phải là cấu hình THẬT: backend 'fake' chỉ để test, nộp bài với fake là sai."""


def test_shipped_configs_use_real_backends(settings):
    assert settings.embed.backend == "bge_m3" and settings.embed.model == "BAAI/bge-m3"
    assert settings.rerank.backend == "bge_reranker" and settings.rerank.model == "BAAI/bge-reranker-v2-m3"


def test_shipped_rerank_is_enabled_with_sane_sizes(settings):
    assert settings.rerank.enabled is True
    assert settings.rerank.batch_size > 0 and settings.rerank.max_length >= 512