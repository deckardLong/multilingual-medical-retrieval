# Rerank by docs

import pandas as pd
from FlagEmbedding import FlagReranker
from common import load_cfg, iter_queries, CFG as cfg, run_path 

chunks = pd.read_parquet(cfg["paths"]["chunks"])
qtext = {q["id"]: q["query"] for q in iter_queries(cfg["paths"]["queries"])}
ret = pd.read_parquet(run_path("retrieval.parquet"))

rr = FlagReranker(cfg["rerank"]["model"], use_fp16=True)
pairs = [(str(qtext[q]), str(chunks.text.iloc[i])) for q, i in zip(ret.qid, ret.chunk_idx)]
ret["rerank"] = rr.compute_score(pairs, batch_size=cfg["rerank"]["batch_size"],
                                 max_length=cfg["rerank"]["max_length"], normalize=True)
ret.to_parquet(run_path("reranked.parquet"))