# Embedding docs

import sys, numpy as np, pandas as pd, os
from FlagEmbedding import BGEM3FlagModel
from common import CFG as cfg

# Load parquet
df = pd.read_parquet(cfg["paths"]["chunks"])
if len(sys.argv) > 1:
    df = df.iloc[:int(sys.argv[1])]

texts = df.text.tolist()
order = np.argsort([len(t) for t in texts])       # sort by length
model = BGEM3FlagModel(cfg["embed"]["model"], use_fp16=True)

E = np.zeros((len(texts), 1024), dtype=np.float16)
BLOCK = 20000
for b in range(0, len(order), BLOCK):
    idx = order[b:b + BLOCK]
    v = model.encode([texts[i] for i in idx], batch_size=cfg["embed"]["batch_size"],
                     max_length=cfg["embed"]["max_length"])["dense_vecs"]
    E[idx] = np.asarray(v, dtype=np.float16)
    print(f"{min(b + BLOCK, len(order))}/{len(order)}", flush=True)

# Save result
os.makedirs(os.path.dirname(cfg["paths"]["emb"]), exist_ok=True)    
np.save(cfg["paths"]["emb"], E)