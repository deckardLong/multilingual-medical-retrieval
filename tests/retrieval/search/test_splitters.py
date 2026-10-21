import pytest
from retrieval.search.decompose.splitters import count_units, split_conjunction, split_questions


def test_count_units_words_and_han():
    assert count_units("xin chào các bạn") == 4 and count_units("糖尿病症状") == 5 and count_units("") == 0


def test_count_units_mixed_scripts_and_punctuation():
    assert count_units("COVID-19 ở trẻ em") == 5            # gạch ngang tách COVID và 19
    assert count_units("a, b; c.") == 3                      # dấu câu không tính
    assert count_units("糖尿病 type 2") == 5                  # mỗi chữ Hán 1 đơn vị


def test_split_questions_on_marks():
    assert split_questions("Triệu chứng là gì? Cách điều trị ra sao?") == ["Triệu chứng là gì", "Cách điều trị ra sao"]
    assert split_questions("症状是什么？如何治疗；预防方法") == ["症状是什么", "如何治疗", "预防方法"]
    assert split_questions("BS. Nguyễn khám bệnh") == ["BS. Nguyễn khám bệnh"]          # dấu chấm viết tắt không tách


@pytest.mark.parametrize("text,expected", [
    ("a?b", ["a", "b"]),
    ("a\n\nb", ["a", "b"]),                      # xuống dòng liên tiếp chỉ tách một lần
    ("a？b；c。d", ["a", "b", "c", "d"]),         # dấu toàn chiều rộng
    ("- triệu chứng\n• điều trị", ["triệu chứng", "điều trị"]),   # bỏ ký hiệu gạch đầu dòng
    ("", []), ("   ", []), ("?;。", []),          # không có nội dung
])
def test_split_questions_edge_cases(text, expected):
    assert split_questions(text) == expected


def test_conjunction_split_requires_all_parts_long_enough():
    assert split_conjunction("nguyên nhân gây bệnh tiểu đường và cách phòng ngừa hiệu quả", 3) == \
        ["nguyên nhân gây bệnh tiểu đường", "cách phòng ngừa hiệu quả"]
    assert split_conjunction("viêm gan B và C", 3) == ["viêm gan B và C"]               # vế ngắn → giữ nguyên
    assert split_conjunction("what causes asthma and how is it treated", 3) == ["what causes asthma", "how is it treated"]
    assert split_conjunction("糖尿病和高血压的症状", 3) == ["糖尿病和高血压的症状"]            # 和 không phải liên từ tách


@pytest.mark.parametrize("sentence,expected", [
    ("nguyên nhân gây bệnh tiểu đường và cả cách phòng ngừa hiệu quả",
     ["nguyên nhân gây bệnh tiểu đường", "cách phòng ngừa hiệu quả"]),         # "và cả" được coi là MỘT liên từ
    ("điều trị bệnh cũng như phòng bệnh hiệu quả", ["điều trị bệnh", "phòng bệnh hiệu quả"]),
    ("what causes asthma AND how is it treated", ["what causes asthma", "how is it treated"]),   # không phân biệt hoa thường
    ("糖尿病的症状有哪些以及如何治疗", ["糖尿病的症状有哪些", "如何治疗"]),
])
def test_conjunction_variants(sentence, expected):
    assert split_conjunction(sentence, 3) == expected


def test_conjunction_inside_a_word_is_not_a_separator():
    assert split_conjunction("candy sandwich andalusia", 1) == ["candy sandwich andalusia"]


def test_three_parts_split_when_all_are_long_enough():
    s = "triệu chứng bệnh gan và nguyên nhân gây bệnh và cách phòng ngừa"
    assert split_conjunction(s, 2) == ["triệu chứng bệnh gan", "nguyên nhân gây bệnh", "cách phòng ngừa"]


def test_all_or_nothing_when_one_part_is_too_short():
    s = "triệu chứng bệnh gan và nguyên nhân gây bệnh và cách"           # vế cuối chỉ 1 từ
    assert split_conjunction(s, 2) == [s]


def test_min_units_boundary_is_inclusive():
    assert split_conjunction("a b c and d e f", 3) == ["a b c", "d e f"]
    assert split_conjunction("a b c and d e f", 4) == ["a b c and d e f"]


@pytest.mark.parametrize("conj", ["và cả", "và", "cũng như", "đồng thời", "and", "as well as"])
def test_every_latin_conjunction_splits(conj):
    s = f"nguyên nhân gây bệnh tiểu đường {conj} cách phòng ngừa hiệu quả"
    assert split_conjunction(s, 3) == ["nguyên nhân gây bệnh tiểu đường", "cách phòng ngừa hiệu quả"]


@pytest.mark.parametrize("conj", ["以及", "并且", "同时", "还有", "而且"])
def test_every_chinese_conjunction_splits(conj):
    assert split_conjunction(f"糖尿病的症状有哪些{conj}如何治疗糖尿病", 3) == ["糖尿病的症状有哪些", "如何治疗糖尿病"]


@pytest.mark.parametrize("sentence", ["triệu chứng bệnh gan.", "  triệu chứng bệnh gan  ", "triệu chứng, bệnh gan:"])
def test_sentence_without_conjunction_is_returned_exactly_as_given(sentence):
    assert split_conjunction(sentence, 1) == [sentence]                  # không bị cắt khoảng trắng/dấu câu ngoài ý muốn