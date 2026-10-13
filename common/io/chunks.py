# Read & write chunks

import os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from common.schema import Chunk

# Define schema
CHUNK_SCHEMA = pa.schema([
    ("chunk_id", pa.string()), 
    ("uid", pa.string()), 
    ("doc_id", pa.string()), 
    ("lang", pa.string()),
    ("start", pa.int32()), 
    ("end", pa.int32()), 
    ("p_start", pa.int32()), 
    ("p_end", pa.int32()),
    ("heading", pa.string()), 
    ("ctx", pa.string()), 
    ("text", pa.string()),
    ("n_tokens", pa.int32()), 
    ("chunker_ver", pa.string()),
])

# Write chunks
def write_chunks(chunks: list[Chunk], path: Path) -> None:

    # Get path => mkdir
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Temp
    tmp = path.with_suffix(".tmp")
    table = pa.Table.from_pylist([c.model_dump() for c in chunks], schema=CHUNK_SCHEMA)
    pq.write_table(table, tmp, compression="zstd")
    os.replace(tmp, path)

# Read chunks
def read_chunks(path: Path) -> list[dict]:
    return pq.read_table(path).to_pylist()