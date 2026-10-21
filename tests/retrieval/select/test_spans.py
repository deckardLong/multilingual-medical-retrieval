from common.schema import Candidate
from retrieval.select import pick_chunks


def c(i, score, start, end):
    return Candidate(chunk_id=f"vi:1#{i}", uid="vi:1", doc_id="1", start=start, end=end, p_start=start, p_end=end,
                     score=score, text="t")


def ids(cs):
    return [x.chunk_id for x in cs]


def test_takes_the_k_best_by_score_regardless_of_input_order():
    cs = [c(0, 0.2, 0, 10), c(1, 0.9, 20, 30), c(2, 0.5, 40, 50), c(3, 0.7, 60, 70)]
    assert ids(pick_chunks(cs, 2)) == ["vi:1#1", "vi:1#3"]


def test_k_larger_than_available_and_k_zero():
    cs = [c(0, 0.2, 0, 10), c(1, 0.9, 20, 30)]
    assert ids(pick_chunks(cs, 5)) == ["vi:1#1", "vi:1#0"] and pick_chunks(cs, 0) == [] and pick_chunks([], 3) == []


def test_overlap_of_exactly_half_is_kept_more_than_half_is_dropped():
    a = c(0, 0.9, 0, 100)
    assert ids(pick_chunks([a, c(1, 0.8, 50, 150)], 2)) == ["vi:1#0", "vi:1#1"]         # 50/100 = 0.5
    assert ids(pick_chunks([a, c(1, 0.8, 49, 149)], 2)) == ["vi:1#0"]                    # 51/100


def test_chunk_contained_in_another_is_dropped():
    assert ids(pick_chunks([c(0, 0.9, 0, 100), c(1, 0.8, 10, 40)], 2)) == ["vi:1#0"]


def test_adjacent_chunks_do_not_overlap():
    assert ids(pick_chunks([c(0, 0.9, 0, 50), c(1, 0.8, 50, 100)], 2)) == ["vi:1#0", "vi:1#1"]


def test_a_dropped_chunk_does_not_block_later_ones():
    a, b, d = c(0, 0.9, 0, 100), c(1, 0.8, 10, 90), c(2, 0.7, 60, 160)       # b trùng a; d chỉ trùng a 40%
    assert ids(pick_chunks([a, b, d], 3)) == ["vi:1#0", "vi:1#2"]


def test_zero_length_chunk_does_not_crash():
    assert ids(pick_chunks([c(0, 0.9, 5, 5), c(1, 0.8, 5, 5)], 2))                        # không chia cho 0


def test_custom_max_overlap():
    a, b = c(0, 0.9, 0, 100), c(1, 0.8, 90, 190)                             # trùng 10%
    assert ids(pick_chunks([a, b], 2, max_overlap=0.05)) == ["vi:1#0"]
    assert ids(pick_chunks([a, b], 2, max_overlap=1.0)) == ["vi:1#0", "vi:1#1"]


def test_input_list_is_not_modified():
    cs = [c(0, 0.2, 0, 10), c(1, 0.9, 20, 30)]
    pick_chunks(cs, 1)
    assert ids(cs) == ["vi:1#0", "vi:1#1"]