from retrieval.embedding.gpu_watch import GpuWatch, WARN_EVERY_SECONDS, throttle_reason

FAST = dict(sm=1300, sm_max=2100, watts=110, temp=72, power_cap=False, thermal=False, hw_slow=False)
CAPPED = dict(FAST, sm=149, watts=34, power_cap=True, thermal=True)


def test_full_clock_is_not_throttled():
    assert throttle_reason(FAST) is None


def test_low_clock_with_power_cap_is_reported_with_causes():
    assert throttle_reason(CAPPED) == "giới hạn công suất, quá nhiệt"


def test_low_clock_without_any_driver_reason_is_just_idle():
    assert throttle_reason(dict(FAST, sm=149)) is None


def test_warns_once_then_waits_for_the_cooldown():
    now = [0.0]
    w = GpuWatch(read=lambda: CAPPED, clock=lambda: now[0])
    first = w.after_slice(4096, 270.0)
    assert first and "15.2 chunk/giây" in first and "Armoury Crate" in first
    now[0] = WARN_EVERY_SECONDS - 1
    assert w.after_slice(4096, 270.0) is None
    now[0] = WARN_EVERY_SECONDS + 1
    assert w.after_slice(4096, 270.0)


def test_no_nvidia_smi_means_no_warning():
    assert GpuWatch(read=lambda: None).after_slice(10, 1.0) is None
