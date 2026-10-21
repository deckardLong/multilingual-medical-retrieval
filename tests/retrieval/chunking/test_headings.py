import pytest
from retrieval.chunking.units import is_heading, title_end, body_lines


@pytest.mark.parametrize("line,expected", [
    ("Triệu chứng của bệnh", True),
    ("Điều trị", True),
    ("Đây là một câu văn kết thúc bằng dấu chấm.", False),
    ("Câu hỏi?", False),
    ("Danh sách:", False),
    ("Ảnh: Getty Images", False),
    ("Theo báo cáo mới", False),
    ("治疗方法", True),
    ("这是一句话。", False),
    ("   ", False),
    ("", False),
])
def test_is_heading(line, expected):
    assert is_heading(line, 80) is expected


def test_heading_too_long_is_not_heading():
    assert not is_heading("a " * 100, 80)


def test_title_end_and_body_lines():
    text = "Tiêu đề\n\nĐoạn 1.\n  \nĐoạn 2.\n"
    assert text[:title_end(text)] == "Tiêu đề"
    got = [text[s:e] for s, e in body_lines(text)]
    assert got == ["Đoạn 1.", "Đoạn 2."]


def test_empty_doc():
    assert title_end("") == 0
    assert title_end("\n\n") == 0
    assert body_lines("Chỉ tiêu đề") == []