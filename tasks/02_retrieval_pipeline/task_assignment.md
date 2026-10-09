# 03 — Phân công hai người và lịch

Hạn: public test **31/10/2026**; private test **1–4/11** (5 lần nộp).

## 1. Phân công

### A — "Retrieval Core" (khối lượng lớn hơn, theo đề nghị của A)

| Thư mục | Việc |
|---|---|
| `retrieval/chunking/` | `structure` (document-structure), `recursive` (fallback), `small_to_big` |
| `retrieval/embedding/` | BGE-M3 (dense + sparse); so sánh với Qwen3-Embedding-4B/8B |
| `retrieval/index/` | Qdrant, upsert incremental, alias theo `embed_ver` |
| `retrieval/search/` | query decomposition (55% truy vấn đa ý), hybrid, fusion RRF |
| `retrieval/rerank/` | cross-encoder (`bge-reranker-v2-m3`) |
| `retrieval/run_index.py`, `api.py` | vòng lặp incremental và hàm `retrieve(query)` |
| `configs/chunk.yaml, embed.yaml, retrieve.yaml, rerank.yaml` | |

### B — "Data & Output"

| Thư mục | Việc |
|---|---|
| `ingestion/sources/viz` | crawl VI/ZH theo truy vấn (`query_rank.py`) |
| `ingestion/sources/en` | pipeline EN/PubMed |
| `ingestion/process/`, `publish/` | normalize, lọc ngôn ngữ, dedupe, shard, validate, push HF |
| `evaluation/` | `dev_set.py`, `metrics.py` (Precision/Recall/F2 macro, mức doc và chunk) |
| `submission/` | `build.py`, `validate.py`, `run_submit.py`, run card |
| `common/` | `hf_sync.py`, `manifest.py` (giữ vai trò thư viện dùng chung) |

### Dùng chung

`common/schema.py`: sửa phải báo người kia, tăng version.

## 2. Những điểm cần lưu ý

1. **A nằm trên đường găng.** Chất lượng điểm phụ thuộc phần lớn vào retrieval, nên nên làm theo thứ tự giá trị:
   1. chunker `structure` + BGE-M3 hybrid + Qdrant (đã đủ chạy end-to-end),
   2. reranker,
   3. query decomposition,
   4. so sánh Qwen3-Embedding (làm sau cùng, tốn GPU nhất).
2. **Eval harness của B phải xong sớm** (1–2 ngày đầu), vì A cần nó mỗi ngày. Trong lúc chờ, A tự dựng dev set tạm: lấy một số truy vấn trong `query.parquet`, dùng BM25 trên 50k doc hiện có để gán nhãn giả, chỉ để so sánh tương đối các chunker.
3. **Lượng dữ liệu là đòn bẩy lớn nhất của B.** Crawl theo truy vấn quyết định recall trần; vì vậy B nên đẩy shard lên HF sớm và đều (không đợi crawl xong), để A thấy tác dụng của dữ liệu mới ngay.
4. **Điểm 0 là việc chung** (xem `02_pipeline_tu_dong.md`, mục 5). B làm `validate.py` đầu tiên; kết quả quyết định B crawl VI/ZH hay dựng EN trước.
5. **Nếu A quá tải:** B nhận lại `search/fusion.py` (tuning trọng số RRF, top-k) hoặc `search/decompose.py`. Hai module này chỉ cần giữ nguyên interface `retrieve(query)`, nên chuyển giao không tốn kém.

## 3. Lịch gợi ý

| Giai đoạn | A | B |
|---|---|---|
| **9–12/10** | `structure.py` + `encode_shard.py` chạy trên 1 shard; Qdrant local | Chốt `schema.py`; `validate.py` + tìm nguyên nhân điểm 0; `hf_sync` + `manifest`; eval harness |
| **13–19/10** | `run_index.py --watch` end-to-end; hybrid RRF; ablation chunking; nộp lần 2 | `ingestion/run.py` tự động; crawl theo truy vấn; push shard đều lên HF; `submission/` hoàn chỉnh |
| **20–26/10** | reranker; decomposition; so BGE-M3 với Qwen3 | pipeline EN/PubMed; dedupe near-dup; hỗ trợ dev set tốt hơn |
| **27–31/10** | đóng băng cấu hình retrieval | chạy lại `run_submit` trên index đầy đủ; nộp bản chính thức; chừa 1–2 ngày dự phòng |
| **1–4/11** | mỗi lần nộp chỉ đổi một biến | quản lý 5 lần nộp, ghi `reports/submissions.csv` |

## 4. Quy tắc làm việc chung

- Đổi schema (Doc/Chunk/Candidate) phải báo người kia và tăng version (`chunker_ver`, `embed_ver`).
- Mỗi lần nộp ghi một dòng vào `reports/submissions.csv`: ngày, `index_ver`, hash config, điểm.
- Một thay đổi một lần: đổi chunker **hoặc** embedding **hoặc** fusion, không đổi nhiều thứ giữa hai lần nộp.
- Nhánh git theo thư mục sở hữu (`feat/ingestion-*`, `feat/retrieval-*`) để ít xung đột merge.