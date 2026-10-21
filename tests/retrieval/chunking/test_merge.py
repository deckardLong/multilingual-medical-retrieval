from retrieval.chunking.merge import merge_short
from retrieval.chunking.units import Piece


def test_short_merges_with_next_same_heading():
    out = merge_short([Piece(0, 5, "A", 5), Piece(6, 50, "A", 60)], 20, 300)
    assert out == [Piece(0, 50, "A", 65)]


def test_short_not_merged_across_headings():
    ps = [Piece(0, 5, "A", 5), Piece(6, 50, "B", 60)]
    assert merge_short(ps, 20, 300) == ps


def test_not_merged_if_exceeds_hard():
    ps = [Piece(0, 5, "A", 5), Piece(6, 50, "A", 298)]
    assert merge_short(ps, 20, 300) == ps


def test_short_last_piece_merges_backward():
    out = merge_short([Piece(0, 50, "A", 60), Piece(51, 60, "B", 5)], 20, 300)
    assert len(out) == 1 and out[0].end == 60


def test_oversize_never_merged():
    ps = [Piece(0, 5, "A", 5), Piece(6, 50, "A", 30, oversize=True)]
    assert merge_short(ps, 20, 300) == ps


def test_empty_and_single():
    assert merge_short([], 20, 300) == []
    p = [Piece(0, 5, "A", 5)]
    assert merge_short(p, 20, 300) == p