# Select to submit

import pickle
import pandas as pd
from common import CFG as cfg, run_path

# Get chunks
chunks = pd.read_parquet(cfg["paths"]["chunks"])
ret = pd.read_parquet(run_path("reranked.parquet"))
ret["doc_id"] = chunks["doc_id"].to_numpy()[ret["chunk_idx"].to_numpy()]

sel = {}
for qid, g in ret.groupby("qid"):
    docs = (g.groupby("doc_id").rerank.max().sort_values(ascending=False)
              .head(cfg["select"]["doc_k"]).index.tolist())
    top = (g[g.doc_id.isin(docs)].sort_values("rerank", ascending=False)
             .head(cfg["select"]["chunk_k"]))
    sel[qid] = (docs, top.chunk_idx.tolist())
with open(run_path("selected.pkl"), "wb") as f:
    pickle.dump(sel, f)