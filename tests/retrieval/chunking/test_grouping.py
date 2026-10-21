from retrieval.chunking.units import body_lines, group_units


def _units(text, target=10, counter=lambda s: len(s.split())):
    lines = body_lines(text)
    counts = [counter(text[s:e]) for s, e in lines]
    return group_units(text, lines, counts, 80, target)


def test_units_cover_lines_and_track_heading():
    text = "T\nMục A\nmột hai ba.\nbốn năm sáu.\nMục B\nbảy tám.\n"
    us = _units(text, target=50)
    assert [u.heading for u in us] == ["Mục A", "Mục B"]
    assert text[us[0].start:us[0].end].startswith("Mục A")
    assert text[us[1].start:us[1].end].endswith("bảy tám.")


def test_unit_splits_when_over_target():
    text = "T\n" + "\n".join(f"{' '.join(['w'] * 6)}." for _ in range(4)) + "\n"
    us = _units(text, target=10)
    assert len(us) >= 2
    assert all(u.tokens <= 12 for u in us)


def test_consecutive_headings_not_orphaned():
    text = "T\nMục A\nMục con\nnội dung ở đây.\n"
    us = _units(text, target=50)
    assert len(us) == 1 and us[0].heading == "Mục con"