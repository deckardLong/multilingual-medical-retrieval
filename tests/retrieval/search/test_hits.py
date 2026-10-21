import pytest
from pydantic import ValidationError
from common.schema import Candidate
from retrieval.search.hits import hit_to_candidate


class Hit:
    def __init__(self, payload, score): self.payload, self.score = payload, score


FULL = dict(chunk_id="vi:1#0", uid="vi:1", doc_id="1", start=0, end=5, p_start=0, p_end=9, text="abc", ctx="T | H",
            lang="vi", heading="H")


def test_hit_to_candidate():
    c = hit_to_candidate(Hit(FULL, 0.7))
    assert isinstance(c, Candidate) and c.score == 0.7 and c.ctx == "T | H" and c.p_end == 9


def test_extra_payload_fields_are_ignored():
    c = hit_to_candidate(Hit(FULL, 0.7))
    assert not hasattr(c, "lang") and not hasattr(c, "heading")


def test_optional_fields_may_be_absent():
    p = {k: v for k, v in FULL.items() if k not in ("text", "ctx")}
    c = hit_to_candidate(Hit(p, 0.1))
    assert c.text is None and c.ctx is None


def test_missing_required_field_raises():
    p = {k: v for k, v in FULL.items() if k != "chunk_id"}
    with pytest.raises(ValidationError):
        hit_to_candidate(Hit(p, 0.1))


def test_score_comes_from_the_hit_and_is_a_float():
    c = hit_to_candidate(Hit({**FULL, "score": 99}, 1))
    assert c.score == 1.0 and isinstance(c.score, float)