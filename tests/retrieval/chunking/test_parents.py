from retrieval.chunking.units import Piece, assign_parents


def test_same_heading_grouped_within_budget():
    ps = [Piece(0, 10, "A", 100), Piece(11, 20, "A", 100), Piece(21, 30, "B", 100)]
    sp = assign_parents(ps, 300)
    assert sp[0] == sp[1] == (0, 20)
    assert sp[2] == (21, 30)


def test_budget_limits_parent():
    ps = [Piece(0, 10, "A", 200), Piece(11, 20, "A", 200)]
    assert assign_parents(ps, 300) == [(0, 10), (11, 20)]


def test_oversize_is_own_parent():
    ps = [Piece(0, 10, "A", 100), Piece(11, 20, "A", 100, oversize=True), Piece(21, 30, "A", 100)]
    sp = assign_parents(ps, 1000)
    assert sp[1] == (11, 20) and sp[0] == (0, 10) and sp[2] == (21, 30)


def test_parent_always_contains_child():
    ps = [Piece(i * 10, i * 10 + 9, "A", 50) for i in range(10)]
    for p, (a, b) in zip(ps, assign_parents(ps, 220)):
        assert a <= p.start and p.end <= b