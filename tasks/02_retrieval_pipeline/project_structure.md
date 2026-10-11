# 01 — Cấu trúc thư mục và hợp đồng giữa hai người

Dự án: `multilingual-medical-retrieval-corpus` (R2AI2026, AI Guru Stage 3)

Phạm vi mới: **crawl toàn bộ** danh sách 4.39M URL của BTC (không còn crawl theo truy vấn). Hai người làm **song song, không ai chờ ai**.

Quy ước: **A** = retrieval (chunking, embedding, index, retrieve, rerank). **B** = dữ liệu và đầu ra (ingestion/crawl, evaluation, submission).

## 1. Nguyên tắc thiết kế

1. **Giao tiếp qua file, không qua code.** Hai bên không import code của nhau. Ba hợp đồng (mục 4) là ba loại file với schema cố định; chốt và đóng băng ngay ngày đầu.
2. **Dữ liệu chảy bất đồng bộ; bên nhận chịu được dữ liệu thiếu.** Crawler đẩy shard lên HF bất cứ lúc nào. Pipeline index của A tự nhận shard mới, chạy được trên 1 shard hay 800 shard. Không bên nào phải chờ "crawl xong".
3. **Mỗi bên có fixture riêng để tự chạy.** `fixtures/` chứa dữ liệu mẫu nhỏ, đủ để A làm việc khi chưa có dữ liệu mới và để B làm submission khi chưa có kết quả retrieval thật.
4. **Shard bất biến, ghi nguyên tử.** Ghi ra file tạm rồi đổi tên, nên A không bao giờ đọc phải shard đang ghi dở. Dữ liệu mới nằm trong shard mới.
5. **Mỗi stage đọc shard và ghi shard dẫn xuất cùng tên.** Manifest (của A) quyết định shard nào cần chạy lại; đổi chunker thì chỉ chunk → embed → upsert chạy lại, crawl không bị ảnh hưởng.
6. **ID xác định.** `chunk_id = f"{uid}#{n}"`; point id Qdrant = UUIDv5 của `chunk_id`, nên upsert idempotent.
7. **HuggingFace chỉ chứa corpus.** Dữ liệu dẫn xuất (chunks, vectors) nằm trên máy GPU của A (xem mục 5).

## 2. Cây thư mục

```
multilingual-medical-retrieval-corpus/
├─ README.md · pyproject.toml · .env.example
├─ configs/
│  ├─ ingestion.yaml                                   # B
│  ├─ chunk.yaml  embed.yaml  retrieve.yaml  rerank.yaml   # A
│  └─ submit.yaml                                      # B
│
├─ common/                          # chỉ 3 file, ĐÓNG BĂNG ở Day 0
│  ├─ schema.py                     # Doc, Chunk, Candidate
│  ├─ config.py                     # Env (.env) + load_yaml + cfg_hash
│  └─ io.py                         # read_docs(shard), write_parquet, file_sha1
│
├─ fixtures/                        # để hai bên tự chạy độc lập
│  ├─ docs/sample.jsonl.zst         # ~200 doc mẫu (cắt từ ~51k đã crawl)
│  ├─ queries/sample.parquet        # ~20 truy vấn
│  ├─ candidates/sample.jsonl       # đầu ra GIẢ của retrieval (cho B)
│  └─ gold/dev_small.jsonl          # nhãn nhỏ để kiểm tra metric
│
├─ ingestion/                       # ── B ──
│  ├─ sources/
│  │  ├─ viz/    urllist.py partition.py frontier.py fetch_async.py extract.py
│  │  └─ en/     pubmed_esearch.py europepmc.py pubtator.py      # thêm sau
│  ├─ process/   normalize.py  lang_filter.py  dedupe.py  shard_writer.py
│  ├─ publish/   validate_docs.py  hf_push.py
│  ├─ monitor/   stats.py                              # tốc độ, tỷ lệ lỗi theo domain, ETA
│  ├─ run_crawl.py                  # --partition a|b : cào + ghi shard cục bộ
│  └─ run_publish.py                # process riêng: validate + đẩy shard lên HF
│
├─ corpus/                          # cache của dataset HF (gitignored)
│  ├─ viz/docs/a/viz-a-0001.jsonl.zst     # a, b = hai phân vùng danh sách URL
│  ├─ viz/docs/b/viz-b-0001.jsonl.zst     # thêm c, d… nếu thêm máy
│  └─ en/docs/pubmed-0001.jsonl.zst       # thêm sau
│
├─ retrieval/                       # ── A ──
│  ├─ chunking/    base.py tokens.py structure.py recursive.py small_to_big.py
│  ├─ embedding/   bge_m3.py encode_shard.py
│  ├─ index/       qdrant_store.py
│  ├─ search/      decompose.py hybrid.py fusion.py select.py
│  ├─ rerank/      cross_encoder.py
│  ├─ settings.py  manifest.py
│  ├─ run_index.py                  # vòng lặp incremental: shard mới → chunk → embed → upsert
│  ├─ run_queries.py                # query.parquet → candidates/<run_id>.jsonl
│  ├─ promote.py                    # chuyển alias Qdrant
│  └─ api.py                        # Retriever.retrieve(query)
│
├─ derived/                         # chỉ ở máy GPU của A (gitignored, KHÔNG đẩy HF)
│  ├─ chunks/<chunk_ver>/{viz,en}/<shard>.parquet
│  └─ vectors/<chunk_ver>__<embed_ver>/<shard>.parquet
│
├─ candidates/                      # A ghi, B đọc (nhỏ, commit vào git)
│  ├─ <run_id>.jsonl
│  └─ <run_id>.run_card.json
│
├─ evaluation/                      # ── B ──
│  ├─ dev_set.py   metrics.py   run_eval.py
├─ submission/                      # ── B ──
│  ├─ build.py   validate.py   run_submit.py
│
├─ queries/query.parquet
├─ state/
│  ├─ ingestion/frontier-{a,b}.sqlite      # B: trạng thái từng URL (pending/ok/fail)
│  └─ retrieval/manifest.parquet           # A: (shard, stage, key, ts)
├─ submissions/<date>_<run_id>.jsonl
├─ reports/                         # crawl_stats.csv, ablation csv, submissions.csv
└─ tests/
   ├─ ingestion/   test_partition.py  test_shard_atomic.py  test_extract.py
   ├─ retrieval/   test_offsets.py  test_idempotent_upsert.py
   └─ submission/  test_submission_schema.py
```

Mỗi file chỉ làm một việc. Mỗi thư mục cấp 1 có đúng một chủ; `common/` đổi phải có đồng ý của cả hai.

## 3. Thư viện nên dùng (không tự viết lại)

| Việc | Thư viện |
|---|---|
| Fetch bất đồng bộ | `aiohttp` (hoặc `httpx`) + `tenacity` cho retry/backoff |
| Trích nội dung bài | `trafilatura` |
| Trạng thái crawl | `sqlite3` (đủ cho 4.39M dòng) |
| Lọc ngôn ngữ | `fasttext` (lid.176) hoặc `langdetect` |
| Dedupe | `content_hash` chính xác; near-dup bằng `datasketch` nếu cần |
| Sync/đẩy HF | `huggingface_hub` (`snapshot_download`, `upload_folder`/`create_commit`) |
| Đọc/ghi shard | `zstandard`, `pyarrow` |
| Splitter fallback | LangChain `RecursiveCharacterTextSplitter` |
| Embedding | `FlagEmbedding` (BGE-M3: dense + sparse) |
| Vector store | Qdrant (named vectors dense + sparse, RRF) |
| Rerank | `bge-reranker-v2-m3` qua `sentence-transformers` CrossEncoder |
| Cấu hình | `pydantic`, `pydantic-settings`, `pyyaml` |

## 4. Ba hợp đồng giữa hai người

Chốt ở Day 0 và đóng băng. Đổi phải báo người kia và tăng version.

### C1 — Doc shard (B ghi → A đọc, qua HF)

Một dòng trong `*.jsonl.zst`:

```json
{"uid": "vi:3367", "lang": "vi", "url": "...", "title": "...",
 "text": "...", "fetched_at": "2026-10-11T10:00:00Z", "content_hash": "sha1..."}
```

Quy tắc về `text` (rất quan trọng vì chunker của A dựa vào cấu trúc dòng):
- **Dòng đầu là tiêu đề bài.** Mỗi đoạn văn và mỗi heading nằm trên **một dòng riêng**, ngăn cách bằng `\n`. Heading là dòng ngắn, không kết thúc bằng dấu câu.
- `text` là văn bản **cuối cùng**: sau khi ghi shard không sửa lại, vì offset của chunk và của file nộp tính trên chính chuỗi này. Mọi bước làm sạch của `ingestion/process/` phải xong trước khi ghi.
- `uid` giữ đúng định dạng ID của BTC.

### C2 — Candidates (A ghi → B đọc, file trong `candidates/`)

Mỗi dòng của `<run_id>.jsonl` là một truy vấn:

```json
{"qid": 1, "query": "...",
 "candidates": [{"chunk_id": "vi:3367#2", "uid": "vi:3367",
                 "start": 123, "end": 456, "score": 0.91}]}
```

`<run_id>.run_card.json` ghi `index_ver`, hash các config, thời điểm, số shard đã index. B chỉ đọc file này; B không biết bên trong A dùng Qdrant hay reranker nào, và không cần chạy GPU.

### C3 — Định dạng nộp và metric (B sở hữu hoàn toàn)

Schema file nộp lên leaderboard, `validate.py`, `metrics.py`. A không phụ thuộc vào phần này.

### Schema nội bộ dùng chung (`common/schema.py`)

`Doc` (khớp C1), `Chunk` (`chunk_id, uid, lang, start, end, heading, ctx, text, chunker_ver`), `Candidate` (khớp C2). `ctx` là chuỗi "tiêu đề | heading" chỉ dùng làm tiền tố khi embed; `text` luôn là `doc.text[start:end]` nguyên văn.

## 5. Dữ liệu trên HuggingFace

| Repo (dataset, private) | Nội dung | Ai ghi |
|---|---|---|
| `<org>/r2ai-corpus` | `viz/docs/{a,b}/*.jsonl.zst`, sau này `en/docs/*` | B (`run_publish.py`) |

Không còn repo `r2ai-derived`. Lý do: ở quy mô toàn bộ corpus, chunks và vectors rất lớn (xem `02_pipeline_tu_dong.md`, mục 4) và có thể vượt hạn mức HF; hơn nữa chunks tái tạo nhanh từ doc, còn vector chỉ A cần, B không dùng. Derived ở lại máy GPU của A; nếu cần sao lưu thì dùng snapshot của Qdrant.