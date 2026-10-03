# Crawler cho thành viên A (VI/ZH)

Crawler này chỉ lấy URL có hostname khớp chính xác với danh sách trong
`domains_a.txt` (44 hostname của `member_01.md`). `www.` và dấu chấm cuối
hostname được chuẩn hóa như `corpus_sources.md`; subdomain khác vẫn là domain
khác và không được crawl nếu không có trong danh sách.

## Cài đặt

Từ thư mục `tasks/01_corpus_collection/crawler`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Đầu vào mặc định là `corpus/raw/links_corpus.parquet` ở repository root, gồm
`id` và `url`. Có thể đổi file bằng `--input`.

## Chạy

```powershell
# Thống kê domain từ toàn bộ Parquet và ghi corpus/viz/input/domain_profile.parquet
python -m corpus_crawler profile

# Smoke test 100 URL đầu tiên của A (không thay thế pilot phân tầng theo domain)
python -m corpus_crawler run --limit 100

# Crawl toàn bộ 44 domain của A; chạy lại sau gián đoạn để tiếp tục
python -m corpus_crawler run

# Xem trạng thái còn lại
python -m corpus_crawler status

# Kiểm tra shard đã đóng
python -m corpus_crawler validate ..\..\..\corpus\viz\docs\a\viz-a-00001.jsonl.zst
```

`run` có thể chạy lại nhiều lần. URL đang dở được đưa về `pending`; kết quả
hoàn tất được ghi vào SQLite trước khi lấy URL tiếp theo. `Ctrl+C` dừng mềm và
đóng shard hiện tại. Nếu tiến trình bị kill/mất điện, các kết quả chưa xuất
shard vẫn nằm trong state DB và được xuất khi chạy lại.

## Giới hạn và tuân thủ website

- Mặc định tối đa 32 request đồng thời toàn cục, nhưng chỉ 1 request đồng thời
  mỗi hostname và tối thiểu 1 giây giữa các request cùng hostname.
- Đọc `robots.txt`, áp dụng `Disallow` và `Crawl-delay`; lỗi robots/network bị
  xử lý fail-closed. Không có cơ chế vượt captcha, paywall hay chặn truy cập.
- Timeout, lỗi HTTP và giới hạn kích thước response được cấu hình trong
  `config.toml`; lỗi tạm thời retry có exponential backoff.
- Tốc độ thực tế vẫn phụ thuộc robots.txt, phản hồi website và kết nối. Không
  chạy đồng thời hai process trên cùng `state-a.sqlite3`.

## Đầu ra

Code không đặt dữ liệu trong thư mục này. Theo kế hoạch, đầu ra nằm ở:

- `corpus/viz/docs/a/viz-a-NNNNN.jsonl.zst`
- `corpus/viz/crawl_log/a/log-a-NNNNN.parquet`
- `corpus/viz/manifest/a/viz-a-NNNNN.manifest.json`
- `corpus/viz/state-a.sqlite3` (checkpoint/resume, không commit)
- `corpus/viz/input/domain_profile.parquet` (lệnh `profile`)

Shard tài liệu và Parquet log được ghi qua file tạm rồi rename. Mặc định đóng
shard sau 20.000 tài liệu; khi dừng mềm có thể tạo shard cuối nhỏ hơn. Dữ liệu
không được tự động commit vào git.

Trước khi crawl hàng loạt, kiểm tra giấy phép/điều khoản của từng website, dung
lượng đĩa, robots policy và pilot extractor. Không bật JS/browser automation:
trang cần JS hoặc bị chặn được ghi log để quyết định thủ công.
