# LUỒNG 1: Crawl dữ liệu Tiếng Việt (VI) & Tiếng Trung (ZH)
Bước 1: Lấy URL mục tiêu & Gửi Request truy cập trang web
Dữ liệu đầu vào: Đọc từ file phân công corpus/viz/input/assignment.parquet (chỉ lấy các URL thuộc các domain được phân cho owner tương ứng: a hoặc b).
File code thực thi: src/crawl/vi.py (với tiếng Việt) và src/crawl/zh.py (với tiếng Trung), hoặc Scrapy Spider dựng trong src/crawl/.
Hành động:
Sử dụng thư viện requests / httpx / Scrapy kèm autothrottle theo domain để kiểm soát tốc độ (tránh bị chặn IP).
Đối với các trang web y khoa cần render JavaScript, kích hoạt Playwright headless browser.
Nếu gặp mã lỗi 429/5xx, thực hiện retry với exponential backoff. Nếu gặp Captcha/Cloudflare, đánh dấu trạng thái blocked và bỏ qua (không cố né bot).
Bước 2: Bóc tách nội dung chính & Chuẩn hóa (Parse & Normalize)
File code thực thi: src/preprocess/normalize.py (kết hợp thư viện trafilatura).
Hành động:
Dùng trafilatura.extract() bóc tách phần thân bài viết (giữ lại Tiêu đề, Heading, Đoạn văn bản; tự động vứt bỏ Header, Footer, Quảng cáo, Menu điều hướng).
Chạy hàm chuẩn hóa chuỗi normalize_text():
Chuyển đổi chuỗi về chuẩn Unicode NFC (bắt buộc cho dấu tiếng Việt).
Xóa ký tự zero-width, ký tự điều khiển ẩn; chuẩn hóa \r\n 
 \n.
Gộp khoảng trắng thừa (tối đa 2 dấu xuống dòng liên tiếp).
Không đổi chữ hoa/thường, không sửa dấu câu để đảm bảo tính nguyên bản.
Ghi nhận vị trí passages: mảng các offset [start, end] của từng đoạn, heading so với toàn bộ chuỗi text.
Tính mã băm content_hash = sha1(text) để đối soát trùng lặp (dup_of).
Bước 3: Ghi dữ liệu ra file Output (Atomic Write)
Để tránh file hỏng khi tiến trình bị ngắt đột ngột, crawler ghi dữ liệu theo cơ chế Atomic Write (ghi ra file tạm .tmp trước, khi đủ 20.000 – 50.000 record thì rename sang file chính thức):
File code thực thi: Module Writer trong src/crawl/vi.py hoặc src/crawl/zh.py.
Các file output được lưu:
File Log trạng thái (Parquet): Lưu lịch sử cào của từng URL (dù thành công, lỗi 404, timeout hay empty).
Đường dẫn: corpus/viz/crawl_log/{owner}/log-{owner}-{seq:05d}.parquet
Ví dụ: corpus/viz/crawl_log/a/log-a-00001.parquet
File Tài liệu văn bản đã chuẩn hóa (JSONL nén zstd): Mỗi dòng là 1 đối tượng JSON theo chuẩn doc.schema.json.
Đường dẫn: corpus/viz/docs/{owner}/viz-{owner}-{seq:05d}.jsonl.zst
Ví dụ: corpus/viz/docs/a/viz-a-00001.jsonl.zst
(Tùy chọn debug): Nếu trang gặp lỗi hoặc thuộc mẫu pilot cần kiểm tra:
Đường dẫn: corpus/viz/debug_html/{owner}/...
Bước 4: Kiểm tra hợp lệ & Tạo Manifest
File code thực thi: src/qc/validate_corpus.py.
Hành động & Output:
Kiểm tra toàn bộ shard vừa ghi: không lỗi cú pháp JSON, text không rỗng, text_len == len(text), offset trong passages không vượt quá độ dài chuỗi.
Tính toán mã SHA-256 của file shard và xuất file Manifest:
Đường dẫn: corpus/viz/manifest/{owner}/viz-{owner}-{seq:05d}.manifest.json
Ví dụ: corpus/viz/manifest/a/viz-a-00001.manifest.json

# LUỒNG 2: Thu thập dữ liệu Tiếng Anh (PubMed theo truy vấn)
Vì dữ liệu tiếng Anh không có danh sách URL trước từ BTC, dữ liệu sẽ được thu thập theo luồng riêng:
Bước 1: Sinh biến thể truy vấn tiếng Anh
File code thực thi: src/query/translate.py (sử dụng LLM mở 
 15B như Qwen).
Input: File câu hỏi test corpus/en/queries/public_test.jsonl.
Output: corpus/en/queries/variants/{owner}/variants-{owner}-{seq:05d}.jsonl (chứa các biến thể: dịch trực tiếp, từ khóa MeSH, tách ý con).
Bước 2: Tìm kiếm PMID & Lưu ứng viên (Candidate Provenance)
File code thực thi: src/crawl/pubmed.py.
Hành động:
Gọi NCBI ESearch API (với API Key đã đăng ký) và Europe PMC API (lọc SRC:MED) để lấy top 100–200 PMID cho mỗi biến thể câu hỏi.
Output lưu trữ:
Bảng ứng viên: corpus/en/candidates/{owner}/cand-{owner}-{seq:05d}.parquet (lưu vết: query nào 
 biến thể nào 
 tìm ra PMID nào).
Bước 3: Lấy Title & Abstract qua PubTator API
File code thực thi: src/crawl/pubmed.py.
Hành động:
So sánh danh sách PMID với cache toàn cục corpus/en/pmid_registry.parquet (nếu PMID đã từng tải thì bỏ qua, chống tải trùng).
Gửi batch request các PMID mới lên PubTator API (https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson).
Trích xuất: Title, Abstract và các metadata y sinh (MeSH, năm xuất bản, journal).
Output lưu trữ:
Cập nhật registry cache: corpus/en/pmid_registry.parquet
Tài liệu tiếng Anh chuẩn hóa: corpus/en/docs/{owner}/en-{owner}-{seq:05d}.jsonl.zst
(Với uid = "en:{pmid}" và doc_id = "{pmid}")
Manifest nghiệm thu: corpus/en/manifest/{owner}/en-{owner}-{seq:05d}.manifest.json
Bảng tóm tắt đường đi của dữ liệu (Data Journey)
Chặng	Bản chất dữ liệu	Code thực thi	File Output sinh ra
1. Request & Log	Trạng thái HTTP, mã phản hồi	src/crawl/vi.py
src/crawl/zh.py	corpus/viz/crawl_log/{a,b}/log-*.parquet
2. Bóc tách & Chuẩn hóa	Nội dung bài viết (Text nguyên văn + Offset)	src/preprocess/normalize.py	Ghi đệm ra file .tmp
3. Lưu trữ Shard	JSONL nén zstd (~20k-50k docs/file)	src/crawl/vi.py (atomic rename)	corpus/viz/docs/{a,b}/viz-*.jsonl.zst
4. Đối soát (QC)	Báo cáo kiểm định, checksum SHA-256	src/qc/validate_corpus.py	corpus/viz/manifest/{a,b}/viz-*.manifest.json
5. Thu thập EN	Abstract bài báo khoa học theo PMID	src/crawl/pubmed.py	corpus/en/docs/{a,b}/en-*.jsonl.zst
corpus/en/candidates/{a,b}/cand-*.parquet
corpus/en/pmid_registry.parquet

___
Các câu lệnh để test: 
Từ thư mục tasks/01_corpus_collection/crawler/:
```bash
# 1. Chạy smoke test 100 URL đầu tiên thuộc 53 domain của Member B
python -m corpus_crawler run --limit 100

# 2. Xem trạng thái kết quả cào thử
python -m corpus_crawler status

# 3. Khi đã ổn định, chạy cào toàn bộ 2.197.280 URL của Member B (chạy nền):
python -m corpus_crawler run
```