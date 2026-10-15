# Entry point

import argparse, logging
from common.config import Env
from retrieval.settings import load_all
from retrieval.embedding import build_embedder
from retrieval.embedding.run import embed_pending

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="chỉ làm N shard đầu")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    s = load_all(Env())
    emb = build_embedder(s.embed)
    r = embed_pending(s, emb, a.limit)
    print(f"{s.embed_tag}: {r.done} shard, {r.n_chunks} chunk, {r.chunks_per_s:.0f} chunk/s, lỗi: {r.failed}")
    return 1 if r.failed else 0

if __name__ == "__main__":
    raise SystemExit(main())