from qdrant_client import models as m
from .errors import IndexingError


def alias_target(client, alias: str) -> str | None:
    for a in client.get_aliases().aliases:
        if a.alias_name == alias:
            return a.collection_name
    return None


def promote(client, collection: str, alias: str, *, min_points: int = 1) -> str | None:
    """Trỏ alias sang `collection` trong MỘT thao tác nguyên tử. Trả về collection cũ (để quay lui)."""
    if not client.collection_exists(collection):
        raise IndexingError(f"collection {collection} không tồn tại")
    n = client.count(collection, exact=True).count
    if n < min_points:
        raise IndexingError(f"collection {collection} chỉ có {n} điểm (< {min_points}), không promote")
    old = alias_target(client, alias)
    ops = []
    if old is not None:
        ops.append(m.DeleteAliasOperation(delete_alias=m.DeleteAlias(alias_name=alias)))
    ops.append(m.CreateAliasOperation(create_alias=m.CreateAlias(collection_name=collection, alias_name=alias)))
    client.update_collection_aliases(change_aliases_operations=ops)
    return old