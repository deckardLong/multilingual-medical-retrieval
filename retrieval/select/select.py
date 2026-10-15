from common.schema import Candidate
from .docs import group_by_uid
from .rules import pick_docs
from .spans import pick_chunks
from .types import Selection


def select(cands: list[Candidate], cfg) -> Selection:
    """Pool đã rerank → danh sách doc và chunk để nộp. Chỉ phụ thuộc SelectCfg nên chỉnh ngưỡng không cần GPU."""
    groups = group_by_uid(cands)
    ranked = [(uid, cs[0].score) for uid, cs in groups.items()]
    kept = pick_docs(ranked, cfg)
    chunks: list[Candidate] = []
    doc_ids: list[str] = []
    for uid in kept:
        chunks += pick_chunks(groups[uid], cfg.chunks_per_doc)
        d = groups[uid][0].doc_id
        if d not in doc_ids:
            doc_ids.append(d)
    return Selection(doc_ids, chunks)