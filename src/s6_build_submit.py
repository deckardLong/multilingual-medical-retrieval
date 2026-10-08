# Build submit

import json, zipfile, pandas as pd
from common import CFG as cfg, iter_queries, run_path

chunks = pd.read_parquet(cfg["paths"]["chunks"])
sel = pd.read_pickle(run_path("selected.pkl"))

out = []
for q in iter_queries(cfg["paths"]["queries"]):
    docs, idxs = sel.get(q["id"], ([], []))              
    out.append({
        "id": int(q["id"]),
        "relevant_docs": [str(d) for d in docs],
        "relevant_chunks": [{"doc_id": str(chunks.doc_id.iloc[i]),
                             "chunk_text": chunks.text.iloc[i]} for i in idxs],
    })

with open(run_path("submission.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
with zipfile.ZipFile(run_path("submission.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.write(run_path("submission.json"), arcname="submission.json")