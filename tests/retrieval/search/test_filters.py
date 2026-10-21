from qdrant_client import models as m
from retrieval.search.filters import lang_filter


def by_lang(langs):
    return m.Filter(must=[m.FieldCondition(key="lang", match=m.MatchAny(any=langs))])


def test_no_langs_means_no_filter():
    assert lang_filter(None) is None and lang_filter([]) is None


def test_single_language():
    assert lang_filter(["vi"]) == by_lang(["vi"])


def test_several_languages_keep_their_order():
    assert lang_filter(["zh", "vi"]) == by_lang(["zh", "vi"])
    assert lang_filter(["zh", "vi"]) != by_lang(["vi", "zh"])          # thứ tự là một phần của kết quả


def test_filter_does_not_alias_the_input_list():
    langs = ["vi"]
    f = lang_filter(langs)
    langs.append("en")
    assert f == by_lang(["vi"])                                         # sửa danh sách gốc không làm đổi bộ lọc