# Load all configs

from common.config import Env, load_cfg, chain
from .bundle import RetrievalSettings
from .checks import check_compat
from .chunk import ChunkCfg
from .embed import EmbedCfg
from .index import IndexCfg
from .retrieve import RetrieveCfg
from .rerank import RerankCfg

# Load all
def load_all(env: Env | None = None) -> RetrievalSettings:
    # Get .env
    env = env or Env()
    chunk = load_cfg("chunk", ChunkCfg, env)
    embed = load_cfg("embed", EmbedCfg, env)
    index = load_cfg("index", IndexCfg, env)
    retrieve = load_cfg("retrieve", RetrieveCfg, env)
    rerank = load_cfg("rerank", RerankCfg, env)
    check_compat(chunk, embed, rerank, retrieve)

    h_chunk = chunk.fingerprint()
    h_embed = chain(embed.fingerprint(), h_chunk)
    h_index = chain(index.fingerprint(), h_embed)
    return RetrievalSettings(env, chunk, embed, index, retrieve, rerank, h_chunk, h_embed, h_index)