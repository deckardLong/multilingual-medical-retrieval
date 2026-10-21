import io
import pytest
from retrieval.progress import Progress
from retrieval.progress.bar import FILE_INTERVAL


class Tty(io.StringIO):
    """StringIO giả làm terminal, để thanh cập nhật liên tục như khi chạy tay."""
    def isatty(self): return True


def lines(stream):
    """Số dòng THẬT trên màn hình: tqdm vẽ lại bằng '\\r' nên mọi lần cập nhật nằm trên cùng một dòng."""
    return stream.getvalue().count("\n")


def test_bar_redraws_in_place_and_never_adds_lines_while_running():
    s = Tty()
    with Progress("embed", 100, "chunk", stream=s) as bar:
        for _ in range(50):
            bar.advance(2)
        assert lines(s) == 0                      # 50 lần cập nhật nhưng vẫn chưa xuống dòng lần nào
    assert lines(s) == 1                          # đóng thanh: đúng một dòng kết thúc


def test_bar_is_closed_even_when_the_stage_raises():
    s = Tty()
    bar = Progress("embed", 10, "chunk", stream=s)
    with pytest.raises(RuntimeError):
        with bar:
            bar.advance(1)
            raise RuntimeError("shard hỏng")
    assert not bar.enabled and lines(s) == 1       # không để lại thanh dang dở


def test_two_stages_run_one_after_another_leaving_one_line_each():
    s = Tty()
    with Progress("chunk", 2, "shard", stream=s) as b1:
        b1.advance(2)
    with Progress("embed", 3, "chunk", stream=s) as b2:
        b2.advance(3)
    assert lines(s) == 2 and "chunk" in s.getvalue() and "embed" in s.getvalue()


def test_non_tty_output_refreshes_slowly_so_log_files_do_not_fill_up():
    """Ghi log ra file: thanh vẫn chạy nhưng chỉ in lại mỗi FILE_INTERVAL giây, không mỗi lần advance."""
    s = io.StringIO()                              # không phải tty
    with Progress("embed", 1000, "chunk", stream=s) as bar:
        for _ in range(100):
            bar.advance()
        assert bar._bar is not None and bar._bar.mininterval == FILE_INTERVAL
        assert lines(s) == 0
    assert lines(s) == 1


def test_closing_the_bar_really_closes_the_underlying_tqdm():
    """Thanh chưa đóng là thứ để lại dòng dang dở khi stage sau bắt đầu vẽ."""
    s = Tty()
    bar = Progress("embed", 10, "chunk", stream=s)
    with bar:
        inner = bar._bar                            # giữ tham chiếu: nếu không close, tqdm.__del__ sẽ che mất lỗi
        assert inner is not None
        bar.advance(10)
    assert inner.disable is True                    # tqdm.close() đặt disable=True