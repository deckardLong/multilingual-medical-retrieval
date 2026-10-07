"""
scriptsbuild_final_manifest.py
Kiểm tra toàn bộ shard của A và B, gộp danh mục vào corpus/final/v1/shards.json
"""
import os
import json
import hashlib
from pathlib import Path

BASE_DIR = Path("corpus/viz/docs")
FINAL_DIR = Path("corpus/final/v1")
FINAL_DIR.mkdir(parents=True, exist_ok=True)

manifest_list = []
total_docs = 0

print("[*] Đang đối soát và gộp các shard từ Member A và Member B...")

for owner in ["a", "b"]:
    owner_dir = BASE_DIR / owner
    if not owner_dir.exists():
        continue
    
    shards = sorted(owner_dir.glob("*.jsonl.zst"))
    for shard_path in shards:
        # Tính SHA-256
        hasher = hashlib.sha256()
        with open(shard_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()
        
        # Đọc manifest đi kèm để lấy số lượng doc
        manifest_file = Path(f"corpus/viz/manifest/{owner}/{shard_path.name}.manifest.json")
        n_docs = 0
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as mf:
                data = json.load(mf)
                n_docs = data.get("n_docs", 0)
        
        total_docs += n_docs
        manifest_list.append({
            "shard": shard_path.name,
            "relative_path": str(shard_path.as_posix()),
            "owner": owner,
            "n_docs": n_docs,
            "sha256": sha256_hash
        })
        print(f"  [✓] Đã ghi nhận: {shard_path.name} ({n_docs:,} docs)")

# Ghi ra file đóng băng final/v1/shards.json
output_file = FINAL_DIR / "shards.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "version": "v1",
        "total_shards": len(manifest_list),
        "total_documents": total_docs,
        "shards": manifest_list
    }, f, indent=2, ensure_ascii=False)

print("\n" + "="*70)
print(f"[✓] HOÀN TẤT ĐÓNG BĂNG CORPUS!")
print(f"• Tổng số Shard:      {len(manifest_list)} files")
print(f"• Tổng số Tài liệu:   {total_docs:,} documents")
print(f"• File danh mục lưu:  {output_file}")