from retrieval.embedding import EncodeStats


def test_chunks_per_second():
    assert EncodeStats(100, 4.0, 12.5).chunks_per_s == 25


def test_zero_duration_does_not_divide_by_zero():
    assert EncodeStats(0, 0.0, 0.0).chunks_per_s == 0.0