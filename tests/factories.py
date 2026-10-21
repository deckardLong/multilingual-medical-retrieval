"""Dữ liệu giả dùng chung cho test."""
from common.schema import Doc


def make_doc(text: str, title: str = "Tiêu đề bài viết", uid: str = "vi:1", lang: str = "vi") -> Doc:
    return Doc(uid=uid, doc_id=uid.split(":")[1], lang=lang, url="https://example.com/x", title=title, text=text)


def paragraph(i: int, words: int = 40) -> str:
    return " ".join(f"từ{i}_{j}" for j in range(words)) + "."


def article(sections: int = 4, paras: int = 3, words: int = 40, uid: str = "vi:1") -> Doc:
    """Bài có dòng tiêu đề, đoạn mở đầu, rồi các mục (heading không dấu câu) mỗi mục vài đoạn."""
    title = "Tiêu đề bài viết"
    lines = [title, "", paragraph(0, words)]
    for s in range(1, sections + 1):
        lines.append(f"Mục số {s} của bài")
        lines += [paragraph(s * 10 + p, words) for p in range(paras)]
    return make_doc("\n".join(lines) + "\n", title=title, uid=uid)


def cand(i: int, text: str, ctx: str | None = None, score: float = 0.5):
    from common.schema import Candidate
    return Candidate(chunk_id=f"vi:1#{i}", uid="vi:1", doc_id="1", start=i, end=i + 1, p_start=i, p_end=i + 1,
                     score=score, text=text, ctx=ctx)

def cand_of(uid: str, i: int, text: str, score: float = 0.5):
    """Candidate của bài `uid` (vd "vi:7", "en:26739349"): chunk thứ i, offset tách biệt giữa các chunk."""
    from common.schema import Candidate
    start = i * 1000
    return Candidate(chunk_id=f"{uid}#{i}", uid=uid, doc_id=uid.split(":", 1)[1], start=start, end=start + len(text),
                     p_start=start, p_end=start + len(text), score=score, text=text)