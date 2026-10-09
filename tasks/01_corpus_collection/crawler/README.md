# Crawler cho thành viên A (VI/ZH)

Crawler này chỉ lấy URL có hostname khớp chính xác với danh sách trong
`domains_a.txt` (44 hostname của `member_01.md`). `www.` và dấu chấm cuối
hostname được chuẩn hóa như `corpus_sources.md`; subdomain khác vẫn là domain
khác và không được crawl nếu không có trong danh sách.

## Cài đặt

Từ thư mục `tasks/01_corpus_collection/crawler`, tạo môi trường riêng cho
crawler. Dùng đường dẫn Python đầy đủ bên dưới để không cài nhầm vào một
virtualenv hoặc Conda environment khác đang được kích hoạt trong terminal:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Không cần chạy PowerShell với quyền Administrator. Nếu `py -3.11` không tìm
thấy Python 3.11, cài Python 3.11 hoặc thay bằng phiên bản Python từ 3.11 trở
lên.

Đầu vào mặc định là `corpus/raw/links_corpus.parquet` ở repository root, gồm
`id` và `url`. Có thể đổi file bằng `--input`.

## Chạy

Chạy các lệnh bên dưới từ cùng thư mục; chúng gọi trực tiếp Python trong
`.venv` để bảo đảm dùng đúng môi trường đã cài crawler:

```powershell
# Thống kê domain từ toàn bộ Parquet và ghi corpus/viz/input/domain_profile.parquet
.\.venv\Scripts\python.exe -m corpus_crawler profile

# Smoke test 100 URL đầu tiên của A (không thay thế pilot phân tầng theo domain)
.\.venv\Scripts\python.exe -m corpus_crawler run --limit 100

# Crawl các domain đang bật trong config; chạy lại để tiếp tục
.\.venv\Scripts\python.exe -m corpus_crawler run

# Xem trạng thái còn lại
.\.venv\Scripts\python.exe -m corpus_crawler status

# Kiểm tra shard đã đóng
.\.venv\Scripts\python.exe -m corpus_crawler validate ..\..\..\corpus\viz\docs\a\viz-a-00001.jsonl.zst
```

`run` có thể chạy lại nhiều lần. URL đang dở được đưa về `pending`; kết quả
hoàn tất được ghi vào SQLite trước khi lấy URL tiếp theo. `Ctrl+C` dừng mềm và
đóng shard hiện tại. Nếu tiến trình bị kill/mất điện, các kết quả chưa xuất
shard vẫn nằm trong state DB và được xuất khi chạy lại.
Checkpoint chấp nhận Parquet được chuyển sang đường dẫn khác nếu kích thước và
thời điểm sửa đổi của file không đổi; nếu một trong hai thay đổi, crawler dừng
để tránh ghép dữ liệu từ input khác vào checkpoint cũ.

`excluded_domains` trong `config.toml` tạm bỏ qua các domain chưa được phép
crawl hoặc liên tục từ chối truy cập. URL chưa xử lý của các domain này vẫn ở
trạng thái `pending`; tiến độ sẽ tiếp tục ở domain khác. Chỉ gỡ domain khỏi
danh sách sau khi đã xác nhận quyền truy cập. Các URL trước đó đã hoàn tất với
trạng thái `blocked` được giữ nguyên trong log và không tự động crawl lại.
Mặc định hiện tại tạm bỏ qua `baohaiphong.vn`, `nhathuoclongchau.com.vn` và
`youmed.vn` vì các lượt thử bị HTTP 403; `khoahocphothong.vn` vì `robots.txt`
liên tục trả HTTP 301; và `laodong.vn`, `baotayninh.vn` vì lần lượt 298 và
1.198 URL đã thử đều trả nội dung rỗng sau bước trích xuất. URL chưa xử lý
của các domain này được giữ lại trong checkpoint và không bị gửi request cho
đến khi domain được gỡ khỏi cấu hình.

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
