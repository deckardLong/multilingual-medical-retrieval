import uuid

_NS = uuid.uuid5(uuid.NAMESPACE_URL, "r2ai/chunk")

def point_id(chunk_id: str) -> str:
    """UUIDv5 xác định từ chunk_id → upsert cùng chunk luôn ghi đè đúng một điểm (idempotent)."""
    return str(uuid.uuid5(_NS, chunk_id))