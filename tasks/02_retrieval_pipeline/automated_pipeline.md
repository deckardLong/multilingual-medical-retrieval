# 02 — Pipeline tự động (crawl toàn bộ, ba pipeline song song)

Ba pipeline chạy **độc lập và đồng thời**. Chúng nối với nhau chỉ qua file (C1 qua HF, C2 trong `candidates/`).

## 1. Luồng tổng thể

```
╔═ B1: ingestion/run_crawl.py --partition a|b (nhiều process/máy, chạy nền) ═══╗
║ urllist → partition → frontier.sqlite (pending/ok/fail, có thể resume)       ║
║ fetch_async (giới hạn theo domain, retry/backoff) → extract (trafilatura)    ║
║ normalize → lang_filter → dedupe → shard_writer (đủ ~5k doc, ghi nguyên tử)  ║
╚═════════════════════════════════╤═══════════════════════════════════════════╝
                                  │ shard cục bộ  corpus/viz/docs/{a,b}/
╔═ B1': ingestion/run_publish.py (process riêng, mỗi ~30 phút) ═══════════════╗
║ validate_docs → hf_push (gom nhiều shard / 1 commit)                         ║
╚═════════════════════════════════╤═══════════════════════════════════════════╝
                                  ▼
                   HF dataset  r2ai-corpus   ◄── hợp đồng C1
                                  │
╔═ A: retrieval/run_index.py --watch (máy GPU, mỗi 10–30 phút) ═══════════════╗
║ snapshot_download (chỉ tải shard mới) → với mỗi shard chưa xong:             ║
║   chunk → embed (GPU) → delete theo uid → upsert Qdrant → ghi manifest       ║
╚═════════════════════════════════╤═══════════════════════════════════════════╝
                                  │ index (Qdrant, alias r2ai_live)
╔═ A: retrieval/run_queries.py ═══╧═══════════════════════════════════════════╗
║ query.parquet → decompose → hybrid dense+sparse RRF → rerank → select        ║
║ → candidates/<run_id>.jsonl + run_card.json            ◄── hợp đồng C2       ║
╚═════════════════════════════════╤═══════════════════════════════════════════╝
                                  ▼
╔═ B2: submission/run_submit.py ══════════════════════════════════════════════╗
║ đọc candidates → gom chunk về doc → ghi submissions/*.jsonl                  ║
║ → validate.py → evaluation/run_eval.py (khi có nhãn) → reports/              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

Mỗi hộp là một process riêng. Crawl không dừng khi A đang index; A không dừng khi B đang sửa `submission/`.

## 2. B1 — Crawl toàn bộ

| Module | Việc |
|---|---|
| `urllist.py` | đọc danh sách BTC (id + url) 4.39M dòng |
| `partition.py` | chia danh sách thành phân vùng `a`, `b`, … theo `hash(id) % N`: các process/máy không bao giờ trùng URL, thêm máy chỉ cần thêm phân vùng |
| `frontier.py` | SQLite theo phân vùng: trạng thái từng URL (`pending / ok / fail(n) / skip`), crash rồi chạy lại là tiếp tục |
| `fetch_async.py` | `aiohttp`, giới hạn đồng thời theo domain, backoff khi gặp 429/5xx, retry có giới hạn |
| `extract.py` | `trafilatura`, giữ cấu trúc dòng theo hợp đồng C1 |
| `process/*` | chuẩn hóa, lọc ngôn ngữ, dedupe, đóng shard ~5k doc |
| `monitor/stats.py` | docs/giây, tỷ lệ lỗi theo domain, ETA → `reports/crawl_stats.csv` |

**Thứ tự duyệt frontier:** xáo trộn ngẫu nhiên có cố định seed, xen kẽ giữa các domain. Hai mục đích: không dồn tải vào một domain (tránh bị chặn), và nếu đến hạn mà chưa cào hết thì phần đã cào vẫn là mẫu **đồng đều** của corpus (recall không lệch về một vài nguồn).

Cấu hình mẫu `configs/ingestion.yaml`:

```yaml
partition: {name: a, of: 2}        # phân vùng a trong 2
fetch:
  concurrency: 200                 # tổng số request đồng thời
  per_host: 4                      # mỗi domain tối đa
  timeout_s: 20
  max_retries: 3
shard: {docs_per_shard: 5000}
publish: {interval_min: 30, batch_shards: 20}
```

Tôn trọng giới hạn của từng site (đặt `per_host` thấp, backoff khi bị 429) để không bị chặn IP.

## 3. A — Index incremental

- **Manifest (của A)** `state/retrieval/manifest.parquet`: mỗi dòng là (shard, stage) với key = `{hash_shard}:{hash_config}`. Hash config nối chuỗi: `h_chunk` → `h_embed = hash(embed, h_chunk)` → `h_index = hash(qdrant, h_embed)`. Đổi chunker thì embed và upsert tự chạy lại; đổi `retrieve.yaml` hay `rerank.yaml` thì không stage nào phải chạy lại.
- **Chạy lại shard an toàn:** trước khi upsert, xóa toàn bộ point của các `uid` trong shard rồi chèn lại (UUIDv5 từ `chunk_id`).
- **Phiên bản trong tên:** `chunk_ver` và `embed_ver` nằm trong đường dẫn `derived/` và tên collection Qdrant, nên mỗi ablation có index riêng. Alias `r2ai_live` chỉ đổi khi collection mới đã qua đánh giá (`promote.py`).
- **Chạy nền:** `python -m retrieval.run_index --watch --interval 900`.
- **Chạy thử trên fixture:** `R2AI_CORPUS_DIR=fixtures/docs python -m retrieval.run_index` khi chưa muốn đụng dữ liệu thật.

## 4. Quy mô dữ liệu (ước tính, cần đo lại)

Các con số dưới đây là ước lượng để lập kế hoạch; đo thật trên shard đầu tiên rồi cập nhật.

| Đại lượng | Ước lượng | Cách đo/ghi chú |
|---|---|---|
| Số chunk | ~25–35 triệu (4.39M doc × ~6–8 chunk) | đếm trên 1–2 shard rồi nhân |
| Vector dense | ~2 KB/chunk fp16 → ~50–70 GB | cần đĩa đủ, `on_disk` cho vector, quantization int8 trong Qdrant |
| Tốc độ embed | đo `chunks/giây` trên GPU của bạn | thời gian embed toàn bộ = số chunk ÷ tốc độ |
| Tốc độ crawl cần có | **≥ 3 doc/giây liên tục** để phủ ~toàn bộ trước ~28/10; mục tiêu 5 doc/giây | tốc độ hiện tại ~5–6 nghìn doc/ngày (~0.07 doc/giây) |

Hai hệ quả:

1. **Crawl là nút thắt, không phải embed.** Nếu crawl đạt vài doc/giây thì lượng chunk mới mỗi giây chỉ vài chục, thấp hơn nhiều so với tốc độ embed của GPU, nên A luôn theo kịp. Embed chỉ bị dồn khi **đổi cấu hình** và phải embed lại toàn bộ.
2. **Chốt cấu hình chunk/embed sớm (Gate ngày 20/10)** bằng ablation trên tập con. Sau mốc đó chỉ tinh chỉnh các tham số không cần re-embed (rerank, fusion, select, decompose), tránh phải embed lại hàng chục triệu chunk.

Cấu hình Qdrant ở quy mô lớn (trong `retrieve.yaml`): vector trên đĩa, quantization scalar int8 giữ trong RAM, HNSW `m` vừa phải; kiểm tra RAM và đĩa của máy GPU trước khi index nhiều shard.

## 5. B2 — Đầu ra và kiểm tra

`submission/validate.py` chạy trước mỗi lần nộp:

1. Mọi `doc_id` có trong danh sách ID của BTC.
2. Offset hợp lệ: `0 <= start < end <= len(text)`.
3. Đúng schema file nộp (C3).
4. Đủ 1,200 truy vấn, không trùng id.
5. Ghi lại `run_id`, `index_ver`, hash config.

B làm và kiểm thử toàn bộ phần này trên `fixtures/candidates/sample.jsonl`, không cần chờ A.

**Nhãn để đánh giá:** hiện chưa có gold công khai ngoài leaderboard. `evaluation/dev_set.py` dựng dev set tổng hợp (ví dụ: truy vấn sinh từ tiêu đề/heading của bài, gold = doc nguồn) để so sánh tương đối giữa các cấu hình. Chỉ dùng cho regression, không phải ước lượng điểm leaderboard. Nếu `details.jsonl` của lần chấm trước có chứa nhãn, ghi thêm vào dev set.

## 6. Điểm 0 của lần nộp đầu

Nguyên nhân chưa xác định (ID đã khớp BTC). Làm song song, không chặn crawl:

1. B chạy `validate.py` đối chiếu doc_id nộp với danh sách BTC và định dạng nộp.
2. A xác nhận offset của chunk khớp định nghĩa của BTC (tính trên chuỗi nào).
3. Cả hai đối chiếu: gold nằm ở VI/ZH hay PubMed/EN (test fetch-recall mức truy vấn). Nếu phần lớn gold là EN thì pipeline EN phải được đẩy lên sớm hơn trong lịch.