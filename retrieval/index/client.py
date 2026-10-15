from qdrant_client import QdrantClient

def make_client(env) -> QdrantClient:
    """qdrant_url=":memory:" → Qdrant chạy trong tiến trình (test/dev, không cần server)."""
    if env.qdrant_url == ":memory:":
        return QdrantClient(":memory:")
    return QdrantClient(url=env.qdrant_url, api_key=env.qdrant_api_key, timeout=120)