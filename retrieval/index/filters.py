from qdrant_client import models as m

def uid_filter(uids: list[str]) -> m.Filter:
    return m.Filter(must=[m.FieldCondition(key="uid", match=m.MatchAny(any=list(uids)))])

def uid_batches(uids: list[str], size: int = 256):
    for i in range(0, len(uids), size):
        yield uids[i:i + size]