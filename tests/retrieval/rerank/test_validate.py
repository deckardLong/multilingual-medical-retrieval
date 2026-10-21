import numpy as np
import pytest
from typing import cast
from retrieval.rerank import RerankError, validate_scores


def test_ok():
    validate_scores([0.0, 0.5, 1.0], 3)


def test_boundaries_are_inclusive():
    validate_scores([0.0, 1.0], 2)


def test_empty_is_valid():
    validate_scores([], 0)


def test_accepts_numpy_floats():
    validate_scores(cast(list[float], [np.float32(0.3), np.float64(0.9)]), 2)


@pytest.mark.parametrize("bad", [[0.1], [0.1, float("nan")], [0.1, 1.5], [0.1, -0.1], [0.1, float("inf")],
                                 [0.1, float("-inf")], [0.1, 0.2, 0.3], [0.1, 1.0000001]])
def test_rejects(bad):
    with pytest.raises(RerankError):
        validate_scores(bad, 2)


def test_message_names_the_bad_position_and_value():
    with pytest.raises(RerankError, match=r"thứ 2.*1\.5"):
        validate_scores([0.1, 0.2, 1.5], 3)


def test_message_reports_wrong_count():
    with pytest.raises(RerankError, match="nhận 1 điểm, cần 2"):
        validate_scores([0.1], 2)