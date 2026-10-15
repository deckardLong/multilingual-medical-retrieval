from qdrant_client import models as m


def lang_filter(langs: list[str] | None) -> m.Filter | None:
    if not langs:
        return None
    return m.Filter(must=[m.FieldCondition(key="lang", match=m.MatchAny(any=list(langs)))])