import warnings
from qdrant_client import models as m
from .errors import IndexingError
from .names import DENSE
from .spec import collection_kwargs

def ensure_collection(client, name: str, index_cfg, embed_cfg) -> bool:
    """Tạo collection (và payload index) nếu chưa có; có rồi thì kiểm tra số chiều khớp. Trả True nếu vừa tạo."""
    if client.collection_exists(name):
        size = client.get_collection(name).config.params.vectors[DENSE].size
        if size != embed_cfg.dim:
            raise IndexingError(f"collection {name} có dim={size}, cấu hình embed dim={embed_cfg.dim}")
        return False
    client.create_collection(name, **collection_kwargs(index_cfg, embed_cfg))
    with warnings.catch_warnings():                 # Qdrant local mode cảnh báo vì không có payload index
        warnings.simplefilter("ignore")
        for field in index_cfg.payload_indexes:
            client.create_payload_index(name, field, m.PayloadSchemaType.KEYWORD)
    return True