import pytest
from retrieval.embedding.batching import is_oom, slices, with_oom_backoff


def test_slices_cover_range_without_gaps():
    assert list(slices(10, 4)) == [(0, 4), (4, 8), (8, 10)]
    assert list(slices(0, 4)) == []
    with pytest.raises(ValueError):
        list(slices(5, 0))


def test_slices_exact_multiple_and_larger_than_n():
    assert list(slices(8, 4)) == [(0, 4), (4, 8)]
    assert list(slices(3, 100)) == [(0, 3)]


def test_slices_tile_every_index_exactly_once():
    for n in range(0, 40):
        for size in (1, 3, 7, 40):
            covered = [i for a, b in slices(n, size) for i in range(a, b)]
            assert covered == list(range(n))


def test_oom_halves_batch_until_it_fits_and_reports_final_size():
    calls = []

    def fn(bs):
        calls.append(bs)
        if bs > 8:
            raise RuntimeError("CUDA out of memory. Tried to allocate ...")
        return "ok"

    result, used = with_oom_backoff(fn, 64)
    assert (result, used) == ("ok", 8) and calls == [64, 32, 16, 8]


def test_no_oom_means_single_call_and_no_callback():
    seen = []
    result, used = with_oom_backoff(lambda bs: bs * 2, 32, on_oom=seen.append)
    assert (result, used) == (64, 32) and seen == []


def test_on_oom_is_notified_with_each_new_size():
    seen = []

    def fn(bs):
        if bs > 2:
            raise RuntimeError("CUDA Out Of Memory")
        return bs

    with_oom_backoff(fn, 16, on_oom=seen.append)
    assert seen == [8, 4, 2]


def test_batch_never_drops_below_min_batch():
    calls = []

    def fn(bs):
        calls.append(bs)
        if bs > 3:
            raise RuntimeError("out of memory")
        return "ok"

    _, used = with_oom_backoff(fn, 10, min_batch=3)
    assert calls == [10, 5, 3] and used == 3          # 5 // 2 = 2 bị nâng lên min_batch


def test_non_oom_errors_propagate_immediately():
    calls = []

    def fn(bs):
        calls.append(bs)
        raise ValueError("lỗi khác")

    with pytest.raises(ValueError):
        with_oom_backoff(fn, 64)
    assert calls == [64]                                # không thử lại


def test_oom_at_minimum_batch_gives_up():
    def fn(bs):
        raise RuntimeError("out of memory")
    with pytest.raises(RuntimeError):
        with_oom_backoff(fn, 4, min_batch=2)


def test_is_oom_detection():
    assert is_oom(RuntimeError("CUDA out of memory. Tried to allocate 2 GiB"))
    assert is_oom(RuntimeError("CUDA Out Of Memory"))
    assert not is_oom(ValueError("shape mismatch"))