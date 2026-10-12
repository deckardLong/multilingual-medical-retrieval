# Crawler cho thành viên A (VI/ZH)

Notebook Kaggle độc lập: [kaggle_crawl.ipynb](../kaggle_crawl.ipynb). Notebook
này dò `links_corpus.parquet` trong `/kaggle/input`, chỉ crawl 44 hostname
Member A, và kiểm tra `query.parquet` nếu có; chỉ file links được dùng để chọn
URL crawl. Nó hiển thị tiến độ và trạng thái theo domain, đồng thời lưu mỗi
kết quả vào SQLite trong `/kaggle/working/member_a_crawl`.

Để tiếp tục vào phiên Kaggle khác, đợi cell dừng xong để tạo
`/kaggle/working/member_a_resume.zip`, chọn **Save Version** để lưu Output,
rồi thêm Output đó làm Input cho notebook mới. Notebook tự khôi phục bundle.
Kaggle không giữ `/kaggle/working` giữa các phiên; nếu phiên bị kill đột ngột,
hãy lưu/đính kèm Output gần nhất trước khi đóng. Khi khởi tạo lần đầu,
checkpoint SQLite cũ `state-a.sqlite3` chỉ được dùng để nhập các kết quả có
cặp ID + URL khớp với snapshot hiện tại; checkpoint cũ không bị sửa.

Khi chưa có bundle/checkpoint, notebook tự đọc các shard `.jsonl.zst` công khai
tại [Hugging Face `corpus/viz/docs/a`](https://huggingface.co/datasets/ai-guru-medical-retrieval/multilingual-medical-retrieval-corpus/tree/main/corpus/viz/docs/a)
và đối chiếu `doc_id` cùng `url` với `links_corpus.parquet`. Các document khớp
được tính là đã crawl và không bị crawl/xuất lặp lại. Thư mục `crawl_log/a`
không có trên Hugging Face hiện tại, nên chỉ có thể resume các URL có document
đã xuất bản; các URL trước đây bị block, rỗng hoặc quá ngắn không có document
vẫn sẽ được xử lý lại.

Crawler CLI bên dưới vẫn chạy trên máy local và dùng checkpoint riêng trong
`corpus/viz/state-a.sqlite3`. Không chạy đồng thời notebook và CLI trên cùng
hostname.

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

# Pilot tối đa 100 URL đang pending chỉ trên một hostname; domain khác giữ nguyên
.\.venv\Scripts\python.exe -m corpus_crawler run --domain sggp.org.vn --max-fetches 100

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
`--domain` chỉ chọn hostname chính xác cho một lượt chạy; `--max-fetches` giới
hạn số URL được nhận xử lý trong lượt đó, tính cả lỗi. Kết hợp hai cờ này để
pilot một domain mà không thay đổi danh sách domain hoặc bỏ URL pending ở các
domain khác. Các tài liệu pilot hợp lệ sẽ được xuất shard khi lượt chạy kết
thúc, kể cả khi chưa đủ `shard_docs`.
Checkpoint chấp nhận Parquet được chuyển sang đường dẫn khác nếu kích thước và
thời điểm sửa đổi của file không đổi; nếu một trong hai thay đổi, crawler dừng
để tránh ghép dữ liệu từ input khác vào checkpoint cũ.

`excluded_domains` trong `config.toml` tạm bỏ qua các domain chưa được phép
crawl hoặc liên tục từ chối truy cập. URL chưa xử lý của các domain này vẫn ở
trạng thái `pending`; tiến độ sẽ tiếp tục ở domain khác. Chỉ gỡ domain khỏi
danh sách sau khi đã xác nhận quyền truy cập. Các URL đã hoàn tất với trạng
thái `blocked` không tự động crawl lại; chỉ thử lại sau khi đã xác nhận quyền
truy cập và chủ động đặt lại trạng thái trong checkpoint.
Mặc định hiện tại tạm bỏ qua `baohaiphong.vn`, `nhathuoclongchau.com.vn` và
`youmed.vn` vì các lượt thử bị HTTP 403; `khoahocphothong.vn` vì `robots.txt`
liên tục trả HTTP 301; và `laodong.vn`, `baotayninh.vn` vì lần lượt 298 và
1.198 URL đã thử đều trả nội dung rỗng sau bước trích xuất. URL chưa xử lý
của các domain này được giữ lại trong checkpoint và không bị gửi request cho
đến khi domain được gỡ khỏi cấu hình.

## Giới hạn và tuân thủ website

- Mặc định tối đa 32 request đồng thời toàn cục, nhưng chỉ 1 request đồng thời
  mỗi hostname và tối thiểu 1 giây giữa các request cùng hostname.
- Scheduler không để nhiều worker cùng chờ trên một hostname. Nó lấy 3 mẫu
  đầu cho mỗi domain còn URL trước khi xếp hạng; sau đó ưu tiên domain có tốc
  độ fetch thành công cao và thời gian xử lý ít dao động. Thống kê được lưu
  trong checkpoint, áp dụng khi resume và xem được bằng lệnh `status`. Việc
  ưu tiên chỉ thay đổi thứ tự URL, không bỏ qua domain hoặc nới lỏng giới hạn
  crawl.
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
