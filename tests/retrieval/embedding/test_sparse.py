from retrieval.embedding.sparse import to_sparse


def test_string_keys_become_sorted_int_indices():
    sv = to_sparse({"30": 0.2, "5": 0.9, "17": 0.4})
    assert sv.indices == [5, 17, 30] and sv.values == [0.9, 0.4, 0.2]


def test_drops_zero_negative_and_non_finite_weights():
    sv = to_sparse({"1": 0.0, "2": -0.1, "3": float("nan"), "4": float("inf"), "5": 0.3})
    assert sv.indices == [5]


def test_empty_input_gives_empty_vector():
    sv = to_sparse({})
    assert sv.indices == [] and sv.values == []