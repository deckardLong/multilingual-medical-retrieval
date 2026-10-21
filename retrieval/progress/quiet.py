"""Tắt mọi thanh tiến độ do thư viện bên dưới tự tạo (FlagEmbedding gọi tqdm khi batch lớn; transformers,
huggingface_hub cũng vậy). Các thư viện này truyền disable= TƯỜNG MINH nên biến môi trường TQDM_DISABLE không
có tác dụng; cách chắc chắn và không phụ thuộc phiên bản là ép disable ngay trong hàm khởi tạo, chỉ trong
khoảng thời gian gọi chúng. Thanh của pipeline được tạo TRƯỚC khi vào đây nên không bị ảnh hưởng."""
from contextlib import contextmanager


@contextmanager
def quiet_tqdm():
    try:
        from tqdm import std as tqdm_std
    except ImportError:                       # không có tqdm thì cũng chẳng có thanh nào để tắt
        yield
        return
    original = tqdm_std.tqdm.__init__

    def muted(self, *a, **kw):
        kw["disable"] = True
        original(self, *a, **kw)

    tqdm_std.tqdm.__init__ = muted
    try:
        yield
    finally:
        tqdm_std.tqdm.__init__ = original