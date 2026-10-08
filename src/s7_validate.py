# Validate before submit

import json, zipfile
from common import CFG as cfg, iter_queries, iter_docs, run_path

with zipfile.ZipFile(run_path("submission.zip")) as z:
    assert z.namelist() == ["submission.json"], z.namelist()
    sub = json.loads(z.read("submission.json"))

qids = {q["id"] for q in iter_queries(cfg["paths"]["queries"])}
assert {r["id"] for r in sub} == qids and len(sub) == len(qids), "thiếu/trùng id"

texts = {}
for d in iter_docs():
    texts.setdefault(d["doc_id"], []).append(d["text"])  

bad = 0
for r in sub:
    assert isinstance(r["id"], int)
    assert isinstance(r["relevant_docs"], list) and isinstance(r["relevant_chunks"], list)
    for c in r["relevant_chunks"]:
        if not any(c["chunk_text"] in t for t in texts.get(c["doc_id"], [])):
            bad += 1
print(f"records = {len(sub)} | Non-verbatim chunks = {bad}")
assert bad == 0