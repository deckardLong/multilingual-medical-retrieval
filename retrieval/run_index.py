"""python -m retrieval.run_index [--watch --interval 900] [--limit N]"""
import argparse, logging, time
from common.config import Env
from retrieval.settings import load_all
from retrieval.chunking import build_chunker, build_counter
from retrieval.embedding import build_embedder
from retrieval.index import make_client, Manifest
from retrieval.pipeline import run_cycle
from retrieval.progress import log_redirect, tqdm_bars

log = logging.getLogger("run_index")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-progress", action="store_true", help="không hiện thanh tiến độ")
    ap.add_argument("--watch", action="store_true", help="lặp mãi, tự nhận shard mới")
    ap.add_argument("--interval", type=int, default=900, help="giây giữa hai vòng khi --watch")
    ap.add_argument("--limit", type=int, default=None, help="tối đa N shard mỗi stage mỗi vòng")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    s = load_all(Env())
    client, manifest = make_client(s.env), Manifest(s.manifest_path)
    cache: dict = {}

    def chunker():
        if "c" not in cache:
            cache["c"] = build_chunker(s.chunk, build_counter(s.chunk.tokenizer), s.chunk_tag)
        return cache["c"]

    def embedder():
        if "e" not in cache:
            cache["e"] = build_embedder(s.embed)
        return cache["e"]

    show = not a.no_progress
    make_bar = tqdm_bars(show)
    with log_redirect(show):
        while True:
            r = run_cycle(s, client, manifest, chunker, embedder, a.limit, make_bar)
            log.info("chunk %d shard | embed %d shard | index %d shard (%d điểm) | lỗi: %s",
                    r.chunk.done, r.embed.done, r.index.done, r.index.n_points, r.failed)
            if not a.watch:
                return 1 if r.failed else 0
            time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())