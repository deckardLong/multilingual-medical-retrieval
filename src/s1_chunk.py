# Chunking step

import os
import pandas as pd
from transformers import AutoTokenizer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from common import iter_docs, CFG as cfg

# Get chunk & token
c = cfg["chunk"]
tok = AutoTokenizer.from_pretrained(cfg["embed"]["model"])

LATIN = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]
SEPS = {
    "vi": LATIN, 
    "en": LATIN, 
    "zh": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", ""]
}
splitters = {
    lang: RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tok, chunk_size=c["target_tokens"], chunk_overlap=c["overlap_tokens"],
        separators=seps
    )
    for lang, seps in SEPS.items()
}

rows, n_docs = [], 0
stat = {
    "short": 0, 
    "notfound": 0
}
for d in iter_docs():
    n_docs += 1
    text = d["text"]
    sp = splitters.get(d["lang"], splitters["vi"])
    pos = 0
    for i, ch in enumerate(sp.split_text(text)):
        s = text.find(ch, pos)              
        if s < 0:
            stat["notfound"] += 1
            continue
        pos = s + 1
        if len(ch) < c["min_chars"]:
            stat["short"] += 1
            continue
        rows.append(dict(chunk_id=f'{d["uid"]}#{i}', uid=d["uid"], doc_id=d["doc_id"],
                         lang=d["lang"], start=s, end=s + len(ch), text=ch))

df = pd.DataFrame(rows)
os.makedirs(os.path.dirname(cfg["paths"]["chunks"]), exist_ok=True)
df.to_parquet(cfg["paths"]["chunks"], index=False)
print(f"docs = {n_docs} chunks = {len(df)} {stat}")
print(df.lang.value_counts())
