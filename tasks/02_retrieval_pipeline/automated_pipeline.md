# 02 — Pipeline tự động (incremental)

Hai pipeline độc lập, nối với nhau chỉ qua dataset `r2ai-corpus` trên HuggingFace. Mỗi người chạy và sửa pipeline của mình mà không chặn người kia.

## 1. Luồng tổng thể

```
╔═ B: ingestion/run.py (chạy liên tục hoặc theo lịch) ════════════════════╗
║ sources/*   crawl (viz theo truy vấn, en từ PubMed) → raw                ║
║ process/    normalize → lang_filter → dedupe → shard_writer              ║
║             (đủ ~5k doc mới đóng 1 shard bất biến)                       ║
║ publish/    validate_docs → hf_push (gom nhiều shard / 1 commit)         ║
╚══════════════════════════════════════╤══════════════════════════════════╝
                                       ▼
                       HF dataset  r2ai-corpus  (hợp đồng Doc)
                                       │
╔═ A: retrieval/run_index.py (vòng lặp trên máy GPU, mỗi 10–30 phút) ═════╗
║ 1. sync_down   list_repo_tree so với manifest → chỉ tải shard mới        ║
║ 2. chunk       shard mới → derived/chunks/<shard>.parquet                ║
║ 3. embed       chunk mới → derived/vectors/<embed_ver>/<shard>.parquet   ║
║ 4. upsert      Qdrant upsert theo point id; doc đổi content_hash thì     ║
║                xóa theo filter uid trước                                 ║
║ 5. push        đẩy chunks + vectors lên HF  r2ai-derived                 ║
║ 6. manifest    ghi (shard, stage, hash, status)                          ║
╚══════════════════════════════════════╤══════════════════════════════════╝
                                       ▼
                        retrieval.api.retrieve(query)
                 (decompose → hybrid dense+sparse RRF → rerank)
                                       │
╔═ B: submission/run_submit.py ═══════╧═══════════════════════════════════╗
║ đọc queries/query.parquet → retrieve từng truy vấn → gom chunk về doc    ║
║ → ghi submissions/*.jsonl → validate.py → ghi run card                   ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## 2. Phía B — `ingestion/`

| Bước | Việc | Ghi chú |
|---|---|---|
| `sources/viz` | crawl theo thứ tự `query_rank.py` (BM25 token slug URL so với truy vấn) | ưu tiên URL có khả năng trả lời 1,200 truy vấn |
| `sources/en` | ESearch + Europe PMC + PubTator | thêm sau |
| `process/normalize` | chuẩn hóa Unicode, bỏ boilerplate | **xong trước khi ghi shard**; sau đó `text` không đổi |
| `process/lang_filter` | giữ vi/zh/en đúng nguồn | |
| `process/dedupe` | trùng `uid` hoặc `content_hash` | shard mới thắng nếu `content_hash` khác |
| `process/shard_writer` | ghi `corpus/viz/docs/{a,b}/viz-{a,b}-NNNN.jsonl.zst` | shard bất biến |
| `publish/validate_docs` | kiểm schema, `uid` duy nhất, text không rỗng | chặn shard hỏng lên HF |
| `publish/hf_push` | `create_commit` gom nhiều file | HF giới hạn ~128 commit/giờ |

## 3. Phía A — `retrieval/`

- **Manifest** `state/manifest.parquet`: mỗi dòng là một cặp (shard, stage) với `input_hash`, `cfg_hash`, `status`, `ts`. Một cặp cần chạy khi chưa `done`, hoặc hash đầu vào/config khác bản đã ghi. Lỗi giữa chừng không làm hỏng shard khác.
- **Sparse/BM25:** dùng sparse vector của BGE-M3 trong Qdrant để upsert incremental. BM25 thuần (`bm25s`) nếu cần thì build lại từ `derived/chunks/*.parquet`.
- **Đổi model embedding:** tạo `vectors/<embed_ver_mới>/` và collection mới, đổi alias khi xong. So BGE-M3 với Qwen3-Embedding trên cùng chunk mà không phá index đang dùng.
- **Dung lượng:** BGE-M3 dense 1024 chiều fp16 ≈ 2 KB/chunk; 2 triệu chunk ≈ 4 GB.
- **Chạy nền:** `python -m retrieval.run_index --watch --interval 900` (tmux/systemd) trên máy GPU.
- **B không cần GPU:** B muốn thử retrieve thì kéo `r2ai-derived` về và upsert vào Qdrant local, không phải embed lại.

## 4. Validate trước khi nộp (`submission/validate.py`)

1. Mọi `doc_id` có trong danh sách ID của BTC.
2. Offset hợp lệ: `0 <= start < end <= len(text)`.
3. Đúng schema file nộp (theo định dạng đã dùng ở lần nộp trước).
4. Đủ 1,200 truy vấn, không trùng id.
5. Run card: `index_ver`, `git sha`, hash các config, thời điểm.
