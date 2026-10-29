# multilingual-medical-retrieval

Hệ thống truy hồi tài liệu y khoa đa ngôn ngữ (Việt/Anh/Trung) cho một truy vấn tiếng Việt — bài thi R2AI2026. Chi tiết đề bài và cách chấm điểm: [competition.md](competition.md).

Đầu vào: câu hỏi tiếng Việt (`queries/query.parquet`). Đầu ra: file `.json` nén `.zip` gồm `relevant_docs` (id tài liệu) và `relevant_chunks` (đoạn trích nguyên văn) cho mỗi câu hỏi, nộp lên dashboard của BTC.

## Luồng tổng thể

Có hai pha tách biệt: **build index** (chạy offline, một lần, lặp lại khi có corpus mới) và **xử lý truy vấn** (chạy mỗi lần cần ra kết quả để nộp).

```
PHA 1 — BUILD INDEX (retrieval.run_index)
──────────────────────────────────────────
corpus/viz/docs/{a,b}/*.jsonl.zst          (tài liệu đã crawl, theo URL của BTC)
        │
        ▼  chunk (structure chunker: heading → unit → merge đoạn ngắn → gắn "cha")
derived/chunks/<chunk_tag>/*.parquet
        │
        ▼  embed (BAAI/bge-m3: vector dense 1024 chiều + vector sparse)
derived/vectors/<embed_tag>/*.parquet
        │
        ▼  index (upsert vào Qdrant, idempotent theo uid tài liệu)
Qdrant collection  r2ai__<embed_tag>__<hash>


PHA 2 — XỬ LÝ TRUY VẤN (retrieval.run_queries)
──────────────────────────────────────────
câu hỏi tiếng Việt
        │
        ▼  decompose (tách câu hỏi nhiều ý thành các truy vấn con, theo luật)
        ▼  encode (bge-m3: mỗi truy vấn con → vector dense + sparse)
        ▼  hybrid search TRONG Qdrant (một lệnh query_points, prefetch lồng nhau):
             mỗi truy vấn con: dense ∪ sparse → RRF → k_fuse
             rồi RRF giữa các truy vấn con → pool k_pool ứng viên (chunk)
        ▼  rerank (BAAI/bge-reranker-v2-m3, cross-encoder, chỉ top_n đầu của pool)
candidates/<run_id>.pool.jsonl             (toàn bộ pool đã rerank — để thử lại select mà không cần GPU)
        │
        ▼  select (retrieval.select): chọn doc theo điểm/ngưỡng, mỗi doc giữ tối đa N chunk
        ▼  expand (submission.expand, tuỳ chọn): nới mỗi chunk ra câu liền trước/sau trong tài liệu gốc
           cho dài gần với đáp án của BTC (đo thực nghiệm: càng dài, chunk-F2 càng cao, tới ~600 từ)
candidates/<run_id>.jsonl                  (đã chọn — input cho bước nộp bài)
        │
        ▼  build + check + pack (submission.run_submit)
submissions/<run_id>.zip                   (file nộp — doc_id dạng số nguyên, < 100 MB)
```

## Vì sao từng bước như vậy

- **Hybrid dense+sparse, RRF hai tầng:** dense (bge-m3) bắt được nghĩa xuyên ngôn ngữ (câu hỏi tiếng Việt khớp tài liệu tiếng Anh/Trung); sparse bắt từ khoá/thuật ngữ y khoa chính xác. RRF tầng 1 gộp hai nhánh cho mỗi truy vấn con; tầng 2 gộp các truy vấn con lại — toàn bộ chạy trong một lệnh Qdrant, không cần gọi lại nhiều lần.
- **Decompose theo luật, không dùng LLM:** câu hỏi dạng "A và B thì làm gì" được tách thành truy vấn con cho A, cho B; vừa tăng recall vừa không tốn thêm một lượt gọi mô hình.
- **Rerank chỉ top_n:** cross-encoder chính xác hơn nhưng chậm hơn hybrid search nhiều; chỉ rerank N chunk đầu (mặc định 80) của pool, phần còn lại giữ thứ tự hybrid với điểm thấp hơn mọi chunk đã rerank.
- **Select tách khỏi pool:** pool (sau rerank) được lưu riêng (`*.pool.jsonl`). Đổi ngưỡng chọn doc/chunk (`retrieval.run_select`) không cần chạy lại GPU/Qdrant — chỉ đọc lại pool và chọn lại trong vài giây.
- **Expand chunk:** theo đặc tả chấm điểm, một chunk chỉ được coi là khớp khi phần chung chiếm ≥ 40% cả đáp án và chunk nộp. Thử nghiệm trên leaderboard cho thấy đáp án của BTC dài hơn chunk gốc nhiều (~100 từ) rất nhiều; nới ra ~600 từ theo đúng câu trong tài liệu gốc (không viết lại nội dung) cải thiện rõ rệt chunk-F2.
- **Index idempotent theo uid:** `upsert_shard` luôn xoá điểm cũ của các `uid` trong shard rồi chèn lại, nên chạy `run_index` nhiều lần (shard mới, hoặc sau khi sửa code chunk/embed) không tạo dữ liệu trùng.

## Cấu trúc thư mục

```
corpus/            tài liệu đã crawl — corpus/viz/docs/{a,b}/*.jsonl.zst (mỗi member một "owner")
                    + corpus/raw/links_corpus.parquet (danh sách {id, url} gốc của BTC)
queries/            query.parquet — tập câu hỏi của BTC
configs/            một file YAML cho mỗi giai đoạn (xem bảng dưới)
common/             schema dùng chung (Doc, Chunk, Candidate), đọc/ghi file, Env/load config
retrieval/
  chunking/         chia tài liệu thành chunk (structure chunker)
  embedding/        encode dense+sparse bằng bge-m3
  index/            tạo collection Qdrant, upsert, alias r2ai_live
  search/           decompose, hybrid search, retriever (gọi embed+search+rerank)
  rerank/           cross-encoder bge-reranker-v2-m3
  select/           chọn doc/chunk cuối cùng từ pool
  pipeline/          run_cycle: nối chunk → embed → index cho shard còn thiếu
  run_index.py, run_embed.py, run_queries.py, run_select.py, promote.py   (entry point)
submission/         build candidates → SubItem/SubChunk → nén zip → kiểm tra đúng đặc tả BTC
                    run_submit.py (entry point)
corpus_sync/        đồng bộ corpus/queries từ HuggingFace (máy có GPU, không tự crawl)
scripts/            notebook crawl chạy trên Kaggle (crawling_data.ipynb) + công cụ phụ
tests/              pytest cho mọi package trên
```

## Các giai đoạn, bằng config nào

| Giai đoạn | Lệnh | Config | Điểm cần biết |
|---|---|---|---|
| Đồng bộ corpus | `python -m corpus_sync.run_fetch` | `corpus_sync.yaml` | Chỉ chạy trên máy có mạng thật ra ngoài; tải shard đã crawl + `links_corpus.parquet` + `query.parquet` từ HuggingFace |
| Chunk + embed + index | `python -m retrieval.run_index` | `chunk.yaml`, `embed.yaml`, `index.yaml` | Tự phát hiện shard mới/đổi; `--watch` để chạy lặp; `.env` quyết định `R2AI_CORPUS_DIR`, `QDRANT_URL` |
| Truy hồi | `python -m retrieval.run_queries` | `retrieve.yaml`, `rerank.yaml` | Ghi checkpoint theo từng câu hỏi — bị ngắt thì chạy lại (không `--fresh`) sẽ tiếp tục đúng chỗ dừng |
| Chọn lại (tuỳ chọn) | `python -m retrieval.run_select` | `retrieve.yaml` (phần `select`) | Chỉ dùng khi muốn đổi ngưỡng chọn mà không truy hồi lại |
| Nộp bài | `python -m submission.run_submit` | `submit.yaml` | Kiểm tra đủ câu hỏi, doc_id hợp lệ, độ dài chunk, dung lượng zip < 100 MB trước khi ghi file |

Tên collection Qdrant và tên các file trung gian (`chunk_tag`, `embed_tag`, `run_id`) đều là hash của chính cấu hình đã dùng — đổi `chunk.yaml`/`embed.yaml`/`index.yaml` sẽ tự tạo ra thư mục/collection mới thay vì ghi đè âm thầm lên dữ liệu cũ.

## Cách chạy end-to-end

### 0. Chuẩn bị môi trường

```bash
python -m venv venv
venv\Scripts\activate          # Windows; macOS/Linux: source venv/bin/activate
pip install qdrant-client FlagEmbedding sentence-transformers torch transformers \
            pydantic pydantic-settings pyarrow zstandard tqdm httpx trafilatura \
            aiohttp protego langdetect scikit-learn pandas numpy huggingface_hub

cp .env.example .env            # điền HF_TOKEN, QDRANT_URL, ... (xem .env.example)
docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 1. Có corpus

Hai cách, không loại trừ nhau:

- **Tải corpus nhóm đã crawl** (nhanh, dùng để build index):
  ```bash
  python -m corpus_sync.run_fetch
  ```
- **Tự crawl thêm** (khi muốn tăng độ phủ so với danh sách link của BTC): chạy `scripts/crawling_data.ipynb` trên Kaggle (notebook tự crawl theo độ ưu tiên khớp với câu hỏi, có checkpoint/resume), rồi chép shard mới vào `corpus/viz/docs/<owner>/`.

### 2. Build index

```bash
python -m retrieval.run_index
```
Chunk mọi tài liệu mới → embed → đưa vào Qdrant. Idempotent, chạy lại an toàn mỗi khi có shard mới. Dùng `--watch` nếu muốn để chạy nền và tự nhận corpus mới liên tục.

### 3. Truy hồi cho toàn bộ câu hỏi

```bash
python -m retrieval.run_queries
```
Ra `candidates/<run_id>.jsonl` (đã chọn doc/chunk) và `candidates/<run_id>.pool.jsonl` (pool đầy đủ, để chọn lại nếu cần). In ra `run_id` ở dòng cuối.

### 4. (Tuỳ chọn) Chọn lại ngưỡng mà không truy hồi lại

```bash
python -m retrieval.run_select --pool candidates/<run_id>.pool.jsonl
```

### 5. Đóng gói bài nộp

```bash
python -m submission.run_submit --candidates candidates/<run_id>.jsonl --note "mô tả ngắn lần chạy"
```
Ra `submissions/<run_id>.zip` — tải lên **My Submissions** tại `http://leaderboard.aiguru.com.vn/`.

### Vòng lặp cải thiện điểm số

```
crawl thêm domain còn thiếu  →  run_index  →  run_queries  →  run_submit  →  xem điểm trên leaderboard
        ▲                                                                           │
        └───────────────────────────── điều chỉnh configs/*.yaml ──────────────────┘
```
