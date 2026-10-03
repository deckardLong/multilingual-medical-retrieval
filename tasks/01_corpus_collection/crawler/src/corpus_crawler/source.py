from __future__ import annotations

from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .text import normalize_hostname


def iter_source_rows(path: Path, batch_size: int = 10_000):
    parquet_file = pq.ParquetFile(path)
    required = {"id", "url"}
    if not required.issubset(parquet_file.schema_arrow.names):
        raise ValueError(f"{path} must contain columns 'id' and 'url'.")
    for batch in parquet_file.iter_batches(
        batch_size=batch_size, columns=["id", "url"]
    ):
        for row in batch.to_pylist():
            yield int(row["id"]), str(row["url"])


def source_row_count(path: Path) -> int:
    return int(pq.ParquetFile(path).metadata.num_rows)


def profile_domains(source_path: Path, output_path: Path) -> tuple[int, int]:
    counts: Counter[str] = Counter()
    invalid = 0
    total = 0
    for _, url in iter_source_rows(source_path):
        total += 1
        domain = normalize_hostname(url)
        if domain is None:
            invalid += 1
        else:
            counts[domain] += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "domain": list(counts.keys()),
            "n_urls": list(counts.values()),
        }
    ).sort_by([("n_urls", "descending"), ("domain", "ascending")])
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    pq.write_table(table, temp_path, compression="zstd")
    temp_path.replace(output_path)
    print(f"URLs profiled: {total:,}; domains: {len(counts):,}; invalid: {invalid:,}")
    print(f"Profile written: {output_path}")
    return total, invalid
