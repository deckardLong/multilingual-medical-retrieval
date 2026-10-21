"""Định dạng bài nộp của BTC: danh sách [{id, relevant_docs, relevant_chunks:[{doc_id, chunk_text}]}]."""
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, TypeAdapter


class SubChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: StrictStr
    chunk_text: StrictStr          # trích nguyên văn từ tài liệu, không viết lại


class SubItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: StrictInt                  # mã truy vấn, số nguyên (không nhận chuỗi "1" hay true)
    relevant_docs: list[StrictStr]
    relevant_chunks: list[SubChunk]


SUBMISSION = TypeAdapter(list[SubItem])