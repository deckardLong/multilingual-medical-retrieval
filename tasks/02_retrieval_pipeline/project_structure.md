# 01 — Cấu trúc thư mục và schema

Dự án: `multilingual-medical-retrieval-corpus` (R2AI2026, AI Guru Stage 3)

Quy ước: mỗi thư mục cấp 1 có **một chủ sở hữu**. **A** = người làm retrieval (chunking, embedding, index, retrieve, rerank). **B** = người làm dữ liệu và đầu ra (ingestion, evaluation, submission).

## 1. Nguyên tắc thiết kế

1. **Shard bất biến, chỉ thêm mới.** Dữ liệu mới nằm trong shard mới, nên thêm dữ liệu không bao giờ buộc index lại từ đầu.
2. **Hai phần ngăn cách bằng một hợp đồng duy nhất: shard doc sạch trên HuggingFace.** `ingestion/` (B) tạo ra nó; `retrieval/` (A) chỉ đọc nó. Hai bên không import code của nhau.
3. **Mỗi stage đọc shard và ghi shard dẫn xuất cùng tên** (`viz-a-0012` → chunks → vectors). Manifest quyết định shard nào cần chạy lại.
4. **ID xác định.** `chunk_id = f"{uid}#{n}"`; point id trong Qdrant là hash của `chunk_id`, nên upsert idempotent.
5. **HuggingFace là nguồn sự thật.** Thư mục local chỉ là cache.

## 2. Cây thư mục

```
multilingual-medical-retrieval-corpus/
├─ README.md · pyproject.toml · .env.example          # HF_TOKEN, QDRANT_URL
├─ configs/
│  ├─ ingestion.yaml                                   # B
│  ├─ chunk.yaml  embed.yaml  retrieve.yaml  rerank.yaml   # A
│  └─ submit.yaml                                      # B
│
├─ common/                          # dùng chung, đổi phải báo người kia
│  ├─ schema.py                     # Doc, Chunk, Candidate
│  ├─ config.py   manifest.py   hf_sync.py   lang.py
│
├─ ingestion/                       # ── B: mọi thứ để có corpus sạch trên HF ──
│  ├─ sources/
│  │  ├─ viz/    frontier.py query_rank.py fetch.py extract.py
│  │  └─ en/     pubmed_esearch.py europepmc.py pubtator.py     # thêm sau
│  ├─ process/   normalize.py  lang_filter.py  dedupe.py  shard_writer.py
│  ├─ publish/   validate_docs.py  hf_push.py
│  └─ run.py                        # raw → shard sạch → push HF
│
├─ corpus/                          # cache local của dataset HF (gitignored)
│  ├─ viz/docs/a/viz-a-0001.jsonl.zst
│  ├─ viz/docs/b/viz-b-0001.jsonl.zst
│  └─ en/docs/pubmed-0001.jsonl.zst                    # thêm sau
│
├─ retrieval/                       # ── A: từ doc sạch đến danh sách ứng viên ──
│  ├─ chunking/    base.py structure.py recursive.py small_to_big.py
│  ├─ embedding/   bge_m3.py encode_shard.py
│  ├─ index/       qdrant_store.py upsert.py
│  ├─ search/      decompose.py hybrid.py fusion.py
│  ├─ rerank/      cross_encoder.py
│  ├─ run_index.py                  # shard mới → chunks → vectors → Qdrant
│  └─ api.py                        # retrieve(query) -> list[Candidate]
│
├─ derived/                         # cache local của dataset HF dẫn xuất (gitignored)
│  ├─ chunks/{viz,en}/<shard>.parquet
│  └─ vectors/<embed_ver>/<shard>.parquet              # chunk_id, dense, sparse
│
├─ evaluation/                      # ── B (A dùng hằng ngày) ──
│  ├─ dev_set.py   metrics.py   run_eval.py
│
├─ submission/                      # ── B ──
│  ├─ build.py   validate.py   run_submit.py
│
├─ queries/query.parquet
├─ state/manifest.parquet           # shard, stage, input_hash, cfg_hash, status, ts
├─ submissions/<date>_<gitsha>_<index_ver>.jsonl
├─ reports/                         # ablation csv, run cards, submissions.csv
└─ tests/
   ├─ ingestion/   test_dedupe.py  test_shard_schema.py
   ├─ retrieval/   test_offsets.py  test_idempotent_upsert.py
   └─ submission/  test_submission_schema.py
```

Mỗi file chỉ làm một việc (ví dụ `structure.py` chỉ chứa `split_units` đã prototype).

### Về thư mục `ingestion/` — nên giữ, kèm hai chỉnh sửa

Hợp lý, vì nó tạo ranh giới sạch: B sở hữu mọi thứ đến lúc có doc sạch trên HF, A sở hữu mọi thứ từ đó trở đi.

1. **Đặt crawler vào `ingestion/sources/`** thay vì thư mục cấp 1 riêng. Mỗi nguồn (viz, en) có một thư mục, thêm nguồn mới không động đến phần còn lại, và toàn bộ phần việc của B nằm trong một thư mục.
2. **Giữ chunking ngoài `ingestion/`.** Tên "ingestion" dễ kéo chunking vào, nhưng chunking cần thử nhiều biến thể (structure / recursive / small-to-big) và gắn với embedding, nên thuộc `retrieval/` của A.

## 3. Thư viện nên dùng (không tự viết lại)

| Việc | Thư viện |
|---|---|
| Sync HF | `huggingface_hub` (`snapshot_download` + `allow_patterns`, `create_commit`) |
| Đọc/ghi shard | `zstandard`, `pyarrow`, hoặc `datasets` |
| Lọc ngôn ngữ | `fasttext` (lid.176) hoặc `langdetect` |
| Dedupe | hash chính xác trên `content_hash`; near-dup bằng `datasketch` (MinHash) nếu cần |
| Splitter fallback | LangChain `RecursiveCharacterTextSplitter` |
| Embedding | `FlagEmbedding` (BGE-M3: dense + sparse) |
| Vector store | Qdrant (named vectors dense + sparse, fusion RRF) |
| Rerank | `bge-reranker-v2-m3` qua `sentence-transformers` CrossEncoder |
| BM25 (tùy chọn) | `bm25s`, build lại từ `derived/chunks/*.parquet` |

## 4. Schema hợp đồng giữa hai người

Đổi bất kỳ schema nào phải báo người kia và tăng version.

**Doc** — B ghi, A đọc (một dòng trong shard `.jsonl.zst`):

```json
{"uid": "vi:3367", "lang": "vi", "url": "...", "title": "...",
 "text": "...", "fetched_at": "2026-10-09T10:00:00Z", "content_hash": "sha1..."}
```

`text` là văn bản **cuối cùng**: sau khi ghi vào shard, không được sửa lại, vì offset của chunk (và của file nộp) tính trên chính chuỗi này. Mọi bước làm sạch của `ingestion/process/` phải xong trước khi ghi shard.

**Chunk** — A ghi (parquet):

| Cột | Ý nghĩa |
|---|---|
| `chunk_id` | `uid#n` |
| `uid` | doc gốc |
| `start`, `end` | offset trong `text` gốc (nguyên văn) |
| `heading` | tiêu đề mục chứa chunk |
| `text` | `doc.text[start:end]` |
| `parent_id` | cho small-to-big |
| `chunker_ver` | đổi → chạy lại shard |

**Candidate** — A trả ra, B (submission) tiêu thụ:

```python
retrieve(query: str) -> list[Candidate(chunk_id, uid, start, end, score)]
```

B chỉ gọi `retrieval.api.retrieve`, không biết bên trong dùng Qdrant hay reranker nào.

## 5. Bố cục trên HuggingFace

| Repo (dataset, private) | Nội dung | Ai ghi |
|---|---|---|
| `<org>/r2ai-corpus` | `viz/docs/{a,b}/*.jsonl.zst`, sau này `en/docs/*` | B (`ingestion/publish/hf_push.py`) |
| `<org>/r2ai-derived` | `chunks/`, `vectors/<ver>/`, `manifest` | A (`retrieval/run_index.py`) |

Thêm tiếng Anh chỉ cần thêm thư mục `en/`; `sync_down` dùng `allow_patterns` nên phía A tự nhận shard mới mà không cần sửa code.