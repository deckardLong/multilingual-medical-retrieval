from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

DOC_STATUSES = {
    "ok",
    "empty",
    "too_short",
    "http_error",
    "timeout",
    "blocked",
    "lang_mismatch",
    "duplicate",
}
PASSAGE_TYPES = {"title", "abstract", "heading", "body"}


def validate_doc(doc: dict[str, Any], owner: str) -> None:
    required = {
        "schema_version",
        "uid",
        "doc_id",
        "lang",
        "source",
        "url",
        "domain",
        "title",
        "text",
        "norm_version",
        "passages",
        "text_len",
        "content_hash",
        "dup_of",
        "fetch",
        "pubmed",
        "owner",
        "code_commit",
    }
    missing = required.difference(doc)
    if missing:
        raise ValueError(f"Document missing required fields: {sorted(missing)}")
    if doc["lang"] not in {"vi", "zh", "en"}:
        raise ValueError(f"Unsupported document language: {doc['lang']!r}")
    if not isinstance(doc["doc_id"], str) or not doc["doc_id"]:
        raise ValueError("doc_id must be a non-empty string")
    if doc["owner"] != owner:
        raise ValueError(f"Document owner must be {owner!r}")
    if doc["uid"] != f"{doc['lang']}:{doc['doc_id']}":
        raise ValueError("uid must be '{lang}:{doc_id}'")
    text = doc["text"]
    if not isinstance(text, str) or doc["text_len"] != len(text):
        raise ValueError("text_len must equal the Unicode character length of text")
    if not text:
        raise ValueError("Documents in a docs shard must have non-empty text")
    expected_hash = "sha1:" + hashlib.sha1(text.encode("utf-8")).hexdigest()
    if doc["content_hash"] != expected_hash:
        raise ValueError("content_hash does not match text")
    fetch = doc["fetch"]
    if not isinstance(fetch, dict) or fetch.get("status") not in DOC_STATUSES:
        raise ValueError("fetch.status is missing or invalid")
    if fetch["status"] == "ok" and not text:
        raise ValueError("status=ok requires non-empty text")
    if not isinstance(doc["passages"], list):
        raise ValueError("passages must be a list")
    for passage in doc["passages"]:
        if (
            passage.get("type") not in PASSAGE_TYPES
            or not isinstance(passage.get("start"), int)
            or not isinstance(passage.get("end"), int)
            or not 0 <= passage["start"] <= passage["end"] <= len(text)
        ):
            raise ValueError(f"Invalid passage offsets: {passage!r}")


def iter_zstd_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    import zstandard

    with path.open("rb") as raw:
        with zstandard.ZstdDecompressor().stream_reader(raw) as reader:
            buffer = bytearray()
            line_number = 0
            while chunk := reader.read(64 * 1024):
                buffer.extend(chunk)
                while (newline := buffer.find(b"\n")) >= 0:
                    line = bytes(buffer[:newline])
                    del buffer[: newline + 1]
                    line_number += 1
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise ValueError(
                                f"Invalid JSON on line {line_number} of {path}"
                            ) from exc
            if buffer.strip():
                line_number += 1
                try:
                    yield json.loads(buffer)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON on line {line_number} of {path}"
                    ) from exc


def validate_shard_file(
    shard_path: Path, owner: str, manifest_path: Path | None = None
) -> tuple[int, str]:
    seen: set[str] = set()
    count = 0
    for doc in iter_zstd_jsonl(shard_path):
        validate_doc(doc, owner)
        uid = doc["uid"]
        if uid in seen:
            raise ValueError(f"Duplicate uid in shard: {uid}")
        seen.add(uid)
        count += 1

    hasher = hashlib.sha256()
    with shard_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["shard"] != shard_path.name:
            raise ValueError("Manifest shard name does not match the file")
        if manifest["owner"] != owner or manifest["n_docs"] != count:
            raise ValueError("Manifest owner or n_docs does not match the shard")
        if manifest["sha256"] != digest:
            raise ValueError("Manifest SHA-256 does not match the shard")
    return count, digest
