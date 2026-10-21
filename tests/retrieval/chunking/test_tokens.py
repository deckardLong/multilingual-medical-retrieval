from retrieval.chunking import build_counter
from retrieval.chunking.tokens import ApproxTokenCounter


def test_approx_counts_words_cjk_and_punct():
    c = ApproxTokenCounter()
    assert c.count("") == 0
    assert c.count("xin chào bạn.") == 4          # 3 từ + dấu chấm
    assert c.count("中文医学") == 4                  # mỗi chữ Hán 1 token


def test_count_many_matches_count():
    c = ApproxTokenCounter()
    xs = ["a b", "", "中文"]
    assert c.count_many(xs) == [c.count(x) for x in xs]


def test_build_counter_approx():
    assert isinstance(build_counter("approx"), ApproxTokenCounter)