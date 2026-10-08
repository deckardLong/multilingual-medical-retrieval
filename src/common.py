# Load config and shards

import glob, json, os, yaml
import pandas as pd
import zstandard as zstd
from typing import cast

# Load config
def load_cfg(path="configs/v0.yaml"):
    return yaml.safe_load(open(path, encoding="utf-8"))

CFG = load_cfg()

# Run path
def run_path(name):
    os.makedirs(CFG["paths"]["runs_dir"], exist_ok=True)
    return os.path.join(CFG["paths"]["runs_dir"], name)

# Iter docs
def iter_docs(pattern=None):
    pattern = pattern or CFG["paths"]["docs_glob"]
    files = sorted(glob.glob(pattern, recursive=True))
    assert files, f"không tìm thấy shard nào theo {pattern}"

    # Iter each doc
    for p in files:
        with zstd.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                if d["fetch"]["status"] == "ok" and d.get("text") and not d.get("dup_of"):
                    yield d

# Iter queries
def iter_queries(path=None):
    df = pd.read_parquet(path or CFG["paths"]["queries"])   # get df    
    assert {"id", "query"} <= set(df.columns), f"cột hiện có: {list(df.columns)}"
    for r in df[["id", "query"]].itertuples(index=False):
        yield {
            "id": int(cast(int | str, r.id)),
            "query": str(r.query)
        }
