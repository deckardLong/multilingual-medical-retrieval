"""Kiểm tra với bge-reranker-v2-m3 THẬT. Mặc định bị bỏ qua; chạy trên máy có GPU:
    R2AI_TEST_REAL_MODEL=1 pytest -m gpu tests/retrieval/rerank/test_real_model.py"""
import math, os
import pytest
from factories import cand

pytestmark = [pytest.mark.gpu,
              pytest.mark.skipif(os.environ.get("R2AI_TEST_REAL_MODEL") != "1", reason="cần model thật + GPU")]

Q_VI = "triệu chứng của sỏi thận"
REL_VI = "Sỏi thận gây đau dữ dội ở vùng hông lưng, buồn nôn và tiểu ra máu."
REL_EN = "Kidney stones cause severe pain in the side and back, nausea and blood in the urine."
REL_ZH = "肾结石会引起腰部剧烈疼痛、恶心和血尿。"
OFF_VI = "Giải bóng đá quốc gia bắt đầu vào tháng tám với hai mươi đội tham dự."
OFF_EN = "The football league season starts in August with twenty teams."
OFF_ZH = "这场足球联赛将于八月开始，共有二十支球队参加。"


@pytest.fixture(scope="module")
def cfg():
    from common.config import Env
    from retrieval.settings import load_all
    return load_all(Env()).rerank


@pytest.fixture(scope="module")
def scorer(cfg):
    from retrieval.rerank import build_pair_scorer
    return build_pair_scorer(cfg)


def test_scores_are_finite_and_inside_unit_range(scorer):
    """Kiểm tra normalize=True thật sự có hiệu lực (logit thô sẽ âm hoặc > 1)."""
    s = scorer.score_pairs([(Q_VI, REL_VI), (Q_VI, OFF_VI), (Q_VI, REL_EN), (Q_VI, OFF_ZH)])
    assert len(s) == 4 and all(math.isfinite(x) and 0.0 <= x <= 1.0 for x in s)


def test_relevant_passage_beats_irrelevant_in_vietnamese(scorer):
    rel, off = scorer.score_pairs([(Q_VI, REL_VI), (Q_VI, OFF_VI)])
    assert rel > off


@pytest.mark.parametrize("rel,off", [(REL_EN, OFF_EN), (REL_ZH, OFF_ZH)])
def test_vietnamese_query_finds_relevant_passage_in_other_languages(scorer, rel, off):
    a, b = scorer.score_pairs([(Q_VI, rel), (Q_VI, off)])
    assert a > b


def test_pair_score_does_not_depend_on_batch_companions(scorer):
    alone = scorer.score_pairs([(Q_VI, REL_VI)])[0]
    batched = scorer.score_pairs([(Q_VI, OFF_ZH), (Q_VI, REL_VI), (Q_VI, OFF_EN)])[1]
    assert abs(alone - batched) < 0.02                   # padding/fp16 chỉ gây sai lệch nhỏ (ngưỡng chưa kiểm chứng)


def test_passage_longer_than_max_length_is_truncated_not_rejected(scorer):
    long_passage = REL_VI + " " + ("Thông tin khác không liên quan. " * 600)
    (s,) = scorer.score_pairs([(Q_VI, long_passage)])
    assert math.isfinite(s) and 0.0 <= s <= 1.0


def test_full_reranker_puts_relevant_chunk_first_and_scores_stay_in_range(cfg):
    from retrieval.rerank import build_reranker
    pool = [cand(0, OFF_VI, score=0.9), cand(1, REL_VI, ctx="Sỏi thận | Triệu chứng", score=0.5), cand(2, OFF_EN, score=0.4)]
    out = build_reranker(cfg).rerank([Q_VI], pool)
    assert out[0].chunk_id == "vi:1#1" and all(0.0 <= c.score <= 1.0 for c in out)