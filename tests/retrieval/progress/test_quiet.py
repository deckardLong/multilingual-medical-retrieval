import io
from tqdm import tqdm
from retrieval.progress import Progress, quiet_tqdm


class Tty(io.StringIO):
    """StringIO giả làm terminal, để tqdm vẽ như khi chạy tay."""
    def isatty(self): return True


def test_a_library_bar_that_asks_to_be_shown_is_still_muted():
    """FlagEmbedding truyền disable=False tường minh khi lô đủ lớn — vẫn phải tắt được."""
    s = Tty()
    with quiet_tqdm():
        for _ in tqdm(range(5), file=s, disable=False):
            pass
    assert s.getvalue() == ""


def test_tqdm_is_restored_even_if_the_block_raises():
    s = Tty()
    try:
        with quiet_tqdm():
            raise RuntimeError("hết VRAM")
    except RuntimeError:
        pass
    for _ in tqdm(range(3), file=s):
        pass
    assert s.getvalue() != ""


def test_the_pipeline_bar_opened_before_the_block_keeps_drawing():
    """Đây là điểm mấu chốt: thanh của mình tạo TRƯỚC khi gọi model nên không bị tắt lây."""
    mine, lib = Tty(), Tty()
    with Progress("embed", 10, "chunk", stream=mine) as bar:
        with quiet_tqdm():
            for _ in tqdm(range(5), file=lib):
                pass
        bar.advance(10)
    assert lib.getvalue() == "" and "10/10" in mine.getvalue()