from dataclasses import dataclass
from common.schema import Candidate


@dataclass
class Selection:
    doc_ids: list[str]              # doc_id (id của BTC) theo thứ tự điểm giảm dần
    chunks: list[Candidate]         # chunk được chọn, nhóm theo doc, trong doc theo điểm giảm dần