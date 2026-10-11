# 03 — Phân công, luồng song song và lịch

Hạn: public test **31/10/2026**; private test **1–4/11** (5 lần nộp). Hôm nay: 11/10.

## 1. Nguyên tắc: không ai đợi ai

Mỗi người có việc để làm ngay từ hôm nay, nhờ ba điều:

1. **Hợp đồng đóng băng ở Day 0** (C1, C2, C3 trong `01_cau_truc_va_schema.md`). Sau đó hai bên không cần hỏi nhau về định dạng.
2. **Fixture** trong `fixtures/`: dữ liệu mẫu để mỗi bên tự chạy khi bên kia chưa giao.
3. **Giao nhận bất đồng bộ:** dữ liệu chảy qua HF, kết quả retrieval chảy qua `candidates/`. Bên nhận chịu được dữ liệu thiếu (dùng bao nhiêu có bấy nhiêu).

### Bảng phụ thuộc: cần gì, chưa có thì dùng gì

| Bên | Cần | Từ | Khi chưa có thì |
|---|---|---|---|
| A | doc để index | B qua HF | dùng ~51k doc đã crawl trong `corpus/viz/docs/{a,b}` và `fixtures/docs`; `run_index --watch` tự nhận shard mới về sau |
| A | dev set/metric | B (`evaluation/`) | A tự chạy tập tự kiểm tra nhỏ (truy vấn từ tiêu đề → doc nguồn, recall@k) bằng một script ngắn; không chặn |
| B2 | kết quả retrieval | A qua `candidates/` | dùng `fixtures/candidates/sample.jsonl` (đầu ra giả đúng schema C2) |
| B2 | quyết định cấu hình retrieval | không cần | B chỉ đọc file candidates |
| B1 | không phụ thuộc ai | | chỉ cần danh sách URL của BTC |

## 2. Phân công

### A — "Retrieval Core"

| Thư mục | Việc |
|---|---|
| `retrieval/chunking/` | `structure`, `recursive`, `small_to_big` |
| `retrieval/embedding/` | BGE-M3 (dense + sparse); so sánh với Qwen3-Embedding |
| `retrieval/index/` | Qdrant, upsert incremental, alias theo `embed_ver`, cấu hình quantization/on-disk |
| `retrieval/search/` | decompose (55% truy vấn đa ý), hybrid RRF, fusion, select (tối ưu F2) |
| `retrieval/rerank/` | cross-encoder `bge-reranker-v2-m3` |
| `retrieval/run_index.py`, `run_queries.py`, `api.py`, `manifest.py` | vòng lặp incremental và xuất candidates |
| `configs/chunk.yaml, embed.yaml, retrieve.yaml, rerank.yaml` | |

### B — "Data & Output", chia hai luồng song song

**B1 — Crawl (chạy nền, hầu như không cần trông):**

| Thư mục | Việc |
|---|---|
| `ingestion/sources/viz` | crawler async toàn bộ 4.39M URL, chia phân vùng `a`, `b`, … |
| `ingestion/process/`, `publish/` | normalize, lọc ngôn ngữ, dedupe, shard, validate, đẩy HF |
| `ingestion/monitor/` | theo dõi tốc độ, lỗi theo domain, ETA |
| `ingestion/sources/en` | pipeline EN/PubMed (làm sau khi crawl VI/ZH ổn định) |

**B2 — Đầu ra:**

| Thư mục | Việc |
|---|---|
| `submission/` | `build.py`, `validate.py`, `run_submit.py`, ghi `reports/submissions.csv` |
| `evaluation/` | `metrics.py` (Precision/Recall/F2 macro, mức doc và chunk), `dev_set.py` |

Crawl chạy không cần người ngồi cạnh nên B làm B2 và EN trong lúc crawl chạy. Nếu thêm máy, chỉ cần thêm phân vùng, không sửa code.

### Dùng chung

`common/` (3 file) đóng băng ở Day 0. Sau đó đổi phải có đồng ý của cả hai.

## 3. Ba hạng mục cần chú ý

1. **Crawl là rủi ro lớn nhất của cả dự án.** Tốc độ hiện tại ~5–6 nghìn doc/ngày; muốn phủ gần hết trước ~28/10 cần ≥ 3 doc/giây liên tục. Đo tốc độ thực của crawler async trong 24 giờ đầu và cập nhật kế hoạch: nếu thấp hơn, mẫu ngẫu nhiên xen kẽ domain đảm bảo phần đã cào vẫn đại diện đều cho corpus.
2. **Gate cấu hình ngày 20/10.** Chốt `chunk.yaml` và `embed.yaml` bằng ablation trên tập con trước mốc này. Sau đó A chỉ chỉnh các tham số không cần embed lại (rerank, fusion, select, decompose). Embed lại toàn bộ là việc tốn hàng giờ đến hàng ngày GPU.
3. **Điểm 0 xử lý song song, không chặn crawl** (xem `02_pipeline_tu_dong.md`, mục 6).

## 4. Lịch

| Ngày | Chung | A (retrieval) | B1 (crawl) | B2 (đầu ra) |
|---|---|---|---|---|
| **11/10 (Day 0)** | Chốt C1/C2/C3, đóng băng `common/`; tạo `fixtures/`; tạo repo HF; skeleton repo (≤ 2 giờ) | | | |
| **11–13/10** | | chunk + embed + Qdrant trên 51k doc có sẵn; `run_queries.py` ra `candidates/` đầu tiên (dù recall thấp) | crawler async + frontier + partition; chạy thử rồi chạy thật; bắt đầu đo docs/giây | `validate.py`, `build.py` trên fixture; kiểm tra điểm 0 |
| **14–19/10** | | ablation chunker (structure vs recursive) và embedding (BGE-M3 vs Qwen3) trên tập con; thử reranker; decompose | giữ crawl ổn định, thêm phân vùng/máy nếu cần; dedupe; `run_publish` đều đặn | `metrics.py`, `dev_set.py`; nộp lần 2 từ candidates thật của A |
| **20/10 — GATE** | chốt `chunk.yaml`, `embed.yaml` | bật `run_index --watch` trên toàn corpus đang về | | |
| **20–26/10** | | tuning rerank / fusion / select / decompose (không cần embed lại) | pipeline EN/PubMed; theo dõi ETA phủ corpus | nộp thử lặp lại; ghi `submissions.csv` |
| **27–31/10** | đóng băng cấu hình | index hết các shard hiện có; `run_queries.py` bản chính thức | dừng ingest sau shard cuối, đẩy HF | `run_submit` bản chính thức; nộp public; chừa 1–2 ngày dự phòng |
| **1–4/11** | | mỗi lần nộp chỉ đổi một biến | | quản lý 5 lần nộp |

Mốc "dừng ingest" (~27/10) là để A index xong shard cuối trước khi nộp; shard đến sau mốc này không dùng cho bản chính thức.

## 5. Quy tắc làm việc chung

- Đổi schema (Doc/Chunk/Candidate) phải báo người kia và tăng version (`chunker_ver`, `embed_ver`).
- Mỗi lần nộp ghi một dòng vào `reports/submissions.csv`: ngày, `run_id`, `index_ver`, hash config, điểm.
- Một thay đổi một lần: đổi chunker **hoặc** embedding **hoặc** fusion, không đổi nhiều thứ giữa hai lần nộp.
- Nhánh git theo thư mục sở hữu (`feat/ingestion-*`, `feat/retrieval-*`) để ít xung đột merge; `candidates/` là nơi duy nhất A ghi dữ liệu cho B.