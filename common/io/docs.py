# Read docs

import io, json
from pathlib import Path
from typing import Iterator
import zstandard
from common.schema import Doc

# Read docs from .zst
def read_docs(path: Path) -> Iterator[Doc]:
    # Get path
    path = Path(path)

    if path.suffix == ".zst":
        with open(path, "rb") as f, zstandard.ZstdDecompressor().stream_reader(f) as r:
            for line in io.TextIOWrapper(r, encoding="utf-8"):
                if line.strip():
                    yield Doc.model_validate(json.loads(line))
    else:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield Doc.model_validate(json.loads(line))