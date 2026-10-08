# Retrieve docs

import numpy as np, pandas as pd, torch
from FlagEmbedding import BGEM3FlagModel
from common import CFG as cfg, iter_queries, run_path

# Get query
queries = list(iter_queries(cfg["paths"]["queries"]))
E = torch.from_numpy(np.load(cfg["paths"]["emb"])).cuda()          

model = BGEM3FlagModel(cfg["embed"]["model"], use_fp16=True)
Q = model.encode([q["query"] for q in queries], batch_size=64, max_length=256)["dense_vecs"]
Q = torch.from_numpy(Q).half().cuda()

rows = []
for b in range(0, len(queries), 200):                             
    sc, ix = (Q[b:b + 200] @ E.T).topk(cfg["retrieve"]["top_n"], dim=1)
    for j in range(sc.shape[0]):
        qid = queries[b + j]["id"]
        for s, i in zip(sc[j].tolist(), ix[j].tolist()):
            rows.append((qid, i, s))
pd.DataFrame(rows, columns=["qid", "chunk_idx", "dense"]).to_parquet(run_path("retrieval.parquet"))