# Bối cảnh bài toán

Tri thức y sinh hiện nay được phân bố không đồng đều giữa các ngôn ngữ. Mặc dù nguồn dữ liệu tiếng Việt ngày càng được mở rộng, nguồn này vẫn còn hạn chế về chiều sâu và chuyên môn. Trong khi đó, tiếng Anh và tiếng Trung sở hữu kho tài nguyên y sinh đồ sộ. Sự chênh lệch này tạo ra một 'khoảng cách thông tin y tế' đáng kể, khiến người dùng sử dụng tiếng Việt gặp nhiều trở ngại trong việc tiếp cận các bằng chứng y học được công bố bằng ngôn ngữ khác.

Xuất phát từ thực trạng đó, cuộc thi hướng tới xây dựng các hệ thống AI có khả năng truy hồi thông tin y sinh đa ngôn ngữ từ các nguồn tiếng Việt, tiếng Anh và tiếng Trung. Với mỗi truy vấn bằng tiếng Việt, hệ thống cần xác định các tài liệu và nội dung liên quan, không phụ thuộc vào ngôn ngữ của nguồn. Ban Tổ chức cung cấp các nguồn dữ liệu để các đội chủ động thu thập, xử lý và xây dựng cơ sở tri thức phục vụ truy hồi. Kết quả được đánh giá ở hai mức độ: tài liệu (document) và đoạn nội dung (chunk), qua đó phản ánh cả khả năng xác định đúng tài liệu liên quan và khả năng định vị chính xác phần nội dung chứa thông tin cần tìm.

Nhiệm vụ có thể được hình thức hoá như sau: Cho tập truy vấn Q = {q₁, q₂, …, qₙ} bằng tiếng Việt và tập các nguồn dữ liệu y sinh đa ngôn ngữ do Ban Tổ chức cung cấp hoặc chỉ định. Các đội tự thiết kế quy trình xây dựng cơ sở tri thức, bao gồm thu thập dữ liệu, tiền xử lý, phân đoạn, lập chỉ mục và truy xuất. Với mỗi truy vấn qᵢ, hệ thống cần tìm và xếp hạng các tài liệu hoặc nội dung liên quan từ các nguồn tiếng Việt, tiếng Anh và tiếng Trung.

# Mục tiêu cuộc thi

Các đội thi cần xây dựng hệ thống AI có khả năng:

## 1. Truy hồi chính xác ở cấp tài liệu

* Xác định đúng các tài liệu liên quan đến truy vấn từ các nguồn dữ liệu y sinh đa ngôn ngữ.
* Thực hiện truy hồi xuyên ngôn ngữ giữa tiếng Việt, tiếng Anh và tiếng Trung thay vì chỉ dựa trên so khớp từ khoá.

## 2. Truy hồi chính xác đoạn nội dung liên quan

* Xác định được các đoạn nội dung thực sự chứa thông tin y khoa liên quan đến truy vấn.
* Cách phân đoạn tài liệu và tổ chức các đơn vị truy hồi do từng đội tự thiết kế.

## 3. Hiểu truy vấn y khoa bằng tiếng Việt

* Hiểu ngôn ngữ tự nhiên tiếng Việt về các thuật ngữ, khái niệm y khoa và lâm sàng.
* Xử lý được truy vấn chứa nhiều thông tin khác nhau trong cùng một câu hỏi.

# Các mốc thời gian quan trọng

* **01 tháng 10, 2026:** Phát hành tập kiểm thử công khai (public test)
* **31 tháng 10, 2026:** Hạn chót nộp bài cho tập kiểm thử công khai
* **01 tháng 11, 2026:** Giai đoạn kiểm thử riêng (private test)
* **04 tháng 11, 2026:** Hạn chót nộp hệ thống
* **11 tháng 11, 2026:** Công bố kết quả chung cuộc

**Lưu ý:** Tất cả các hạn chót đều là 23:59 theo giờ Việt Nam (UTC+07:00).

# Quy định về dữ liệu bên ngoài và mô hình ngôn ngữ huấn luyện trước (PLMs)

Để đảm bảo sự công bằng trong cuộc thi, người tham gia phải cung cấp nguồn dữ liệu. Người tham gia được phép sử dụng dữ liệu từ các nguồn bên ngoài, tuy nhiên phải trích dẫn rõ ràng và cung cấp đầy đủ thông tin về nguồn gốc dữ liệu để Ban tổ chức có thể kiểm tra, xác minh khi cần thiết.

Người tham gia có thể sử dụng các mô hình ngôn ngữ huấn luyện trước và các LLM có dữ liệu huấn luyện và/hoặc mô hình được công khai (ví dụ: Hugging Face hoặc các trang tương tự), nhưng không được sử dụng các LLM có mô hình đóng (ví dụ: GPT-4o, Gemini, ...). Ngoài ra, người tham gia chỉ được sử dụng các mô hình được phát hành trước ngày 1 tháng 8 năm 2026 (giờ Việt Nam) có kích thước nhỏ hơn hoặc bằng 15B.

# Phương pháp đánh giá

Hiệu suất hệ thống trên nhiệm vụ truy hồi được đánh giá ở hai cấp độ: tài liệu và đoạn nội dung, bằng các chỉ số Độ chính xác (Precision), Độ bao phủ (Recall) và F2. Các chỉ số được tính riêng cho từng truy vấn, sau đó lấy trung bình trên toàn bộ tập truy vấn (macro-average).

## 3.1 Truy hồi tài liệu (Cấp Document)

Với mỗi truy vấn, gọi D là tập tài liệu được truy hồi và G là tập tài liệu liên quan theo nhãn tham chiếu.

### Precision

$$
Precision = \frac{|D \cap G|}{|D|}
$$

### Recall

$$
Recall = \frac{|D \cap G|}{|G|}
$$

## 3.2 Truy hồi đoạn nội dung (Cấp Chunk)

Với mỗi truy vấn, gọi C là tập chunk_text được truy hồi và I là tập các phần thông tin cần thiết trong những tài liệu liên quan.

Một chunk_text được tính là relevant nếu chứa nội dung tương ứng hoặc overlap đủ với ít nhất một phần thông tin cần thiết trong I.

### Precision

$$
Precision =
\frac{\text{Số chunk relevant}}
{\text{Tổng số chunk được truy hồi}}
$$

### Recall

$$
Recall =
\frac{\text{Số phần thông tin cần thiết được bao phủ}}
{\text{Tổng số phần thông tin cần thiết}}
$$

Độ dài mỗi chunk_text được khuyến nghị không quá khoảng 1.024 tokens.

## 3.3 Độ đo F2 macro

Với mỗi truy vấn, điểm F2 được tính từ Precision và Recall của truy vấn đó:

$$
F2 =
\frac{5 \times Precision \times Recall}
{4 \times Precision + Recall}
$$

Điểm F2 macro được tính bằng trung bình cộng điểm F2 của tất cả các truy vấn.

# Dashboard kết quả

Các đội thi nộp kết quả dự đoán trực tiếp trên hệ thống Dashboard chính thức của cuộc thi. Mỗi lần nộp bài cần đảm bảo các yêu cầu sau:

* **Định dạng file:** kết quả được nộp dưới dạng file chuẩn theo mẫu do Ban Tổ chức quy định, với cấu trúc trường dữ liệu tuân thủ đúng đặc tả.
* **Nội dung file:** bao gồm kết quả trả lời cho toàn bộ câu hỏi trong bộ dữ liệu kiểm thử. Bài nộp bị thiếu câu hoặc không đúng định dạng sẽ không được đánh giá.
* **Số lần nộp:** mỗi đội được giới hạn số lần nộp bài mỗi ngày nhằm đảm bảo tính công bằng và tránh hiện tượng dò đáp án.

# Định dạng nộp bài

Thí sinh phải nộp file kết quả truy hồi ở định dạng `.json`. File phải tuân theo cấu trúc sau:

```json
[
  {
    "id": <integer>,
    "relevant_docs": ["<id_tài_liệu>"],
    "relevant_chunks": [
      {
        "doc_id": "<id_tài_liệu>",
        "chunk_text": "<nội_dung_chunk>"
      }
    ]
  },
  ...
]
```

Trong đó:

* `id`: Mã định danh của câu hỏi, kiểu số nguyên (integer).
* `relevant_docs`: Danh sách mã định danh của các tài liệu được dự đoán là liên quan.
* `relevant_chunks`: Danh sách các đoạn nội dung được dự đoán là liên quan. Mỗi đoạn cần chỉ rõ tài liệu nguồn qua `doc_id` và nội dung của đoạn qua `chunk_text`.
* `doc_id`: Mã định danh của tài liệu gốc chứa đoạn nội dung được truy hồi. Đối với tài liệu tiếng Việt và tiếng Trung, doc_id là mã id tương ứng trong tệp nguồn do Ban Tổ chức cung cấp. Đối với tài liệu tiếng Anh, nguồn dữ liệu sử dụng là PubMed và PMID được dùng làm doc_id.
* `chunk_text`: Nội dung của đoạn văn bản được hệ thống truy hồi từ tài liệu tương ứng với doc_id. chunk_text phải là nội dung được trích xuất từ tài liệu gốc, không phải nội dung được viết lại hoặc sinh mới bởi hệ thống.

## Ví dụ bài nộp

```json
[
  {
    "id": 1,
    "relevant_docs": [
      "doc_id1",
      "doc_id2"
    ],
    "relevant_chunks": [
      {
        "doc_id": "doc_id1",
        "chunk_text": "Đoạn nội dung liên quan thứ nhất được trích từ tài liệu doc_id1."
      },
      {
        "doc_id": "doc_id1",
        "chunk_text": "Đoạn nội dung liên quan thứ hai được trích từ một vị trí khác trong tài liệu doc_id1."
      },
      {
        "doc_id": "doc_id2",
        "chunk_text": "Đoạn nội dung liên quan được trích từ tài liệu doc_id2."
      }
    ]
  }
]
```

Nếu hệ thống không dự đoán được kết quả ở một mức, thí sinh vẫn phải cung cấp trường tương ứng với danh sách rỗng.

Sau đó nén file `.json` lại, vào mục My Submissions trên http://leaderboard.aiguru.com.vn/, và tải lên file đã nén.

## Lưu ý

* Tất cả các file kết quả phải được nén trong một file ZIP, chỉ chứa duy nhất một file (không nằm trong thư mục con).
* Xin lưu ý rằng các bài nộp bị thiếu file hoặc thiếu câu sẽ không được đánh giá và sẽ không bị tính vào số lần nộp tối đa cho phép.

# Quy định nộp bài

* Mỗi đội được phép nộp tối đa 10 bài mỗi ngày.
* Số bài nộp tối đa cho mỗi người dùng trong Vòng riêng (Private Phase) là 5 bài tổng cộng. Vì vậy, hãy chọn lựa các bài nộp ở Vòng riêng một cách cẩn thận.
* Mỗi đội cần có một tên người dùng đại diện.
* Kết quả cuối cùng sẽ không được xem là chính thức cho đến khi một bài báo mô tả phương pháp (working notes paper) với mô tả đầy đủ về các phương pháp được nộp.
* Ban Tổ chức Cuộc thi có toàn quyền, theo quyết định riêng của mình, loại bất kỳ thí sinh nào có bài nộp không tuân thủ tất cả các yêu cầu.

# Dữ liệu cuộc thi

## Ban Tổ chức cung cấp

* **Danh sách nguồn dữ liệu:** các liên kết tới nguồn bài viết y khoa tiếng Việt và tiếng Trung để các đội chủ động thu thập, xử lý và xây dựng cơ sở tri thức phục vụ truy hồi. Đối với tiếng Anh, các đội có thể chủ động tìm kiếm tài liệu từ PubMed thông qua các API như NCBI Entrez E-utilities hoặc Europe PMC.
* **Bộ dữ liệu kiểm thử (test set):** tập câu hỏi bằng tiếng Việt, được sử dụng làm căn cứ chấm điểm và đánh giá hệ thống của các đội thi.

Ban Tổ chức không cung cấp quy trình embedding/indexing sẵn có. Các đội thi được toàn quyền chủ động trong việc:

* Xây dựng hoặc lựa chọn mô hình embedding đa ngôn ngữ phù hợp với dữ liệu y học.
* Thiết kế chiến lược lập chỉ mục và tìm kiếm.
* Xây dựng cơ chế reranking, hậu xử lý.
* Các tập dữ liệu mở khác về y học mà đội thi có thể hợp pháp sử dụng để huấn luyện/đánh giá bổ trợ.

# Tập câu hỏi truy vấn

Tập câu hỏi truy vấn được cung cấp dưới dạng tệp JSONL. Mỗi dòng là một đối tượng JSON hợp lệ, gồm:

* `id`: Mã định danh của truy vấn, kiểu số nguyên (integer).
* `query`: Nội dung truy vấn y khoa bằng tiếng Việt, kiểu chuỗi (string).

```json
{
  "id": <integer>,
  "query": "<string>"
}
```

## Ví dụ

```json
{
  "id": 1,
  "query": "Cần làm gì đối với tình trạng tắc nghẽn đường tiết niệu do sỏi thận?"
}
```

# Nguồn dữ liệu được cung cấp

Đối với dữ liệu tiếng Việt và tiếng Trung, Ban Tổ chức cung cấp danh sách URL của các bài viết y khoa dưới dạng tệp JSONL. Mỗi dòng là một đối tượng JSON hợp lệ, gồm:

* `id`: Mã định danh của nguồn, kiểu số nguyên (integer).
* `url`: URL dẫn tới bài viết gốc, kiểu chuỗi (string).

```json
{
  "id": 1,
  "url": "https://example.com/article"
}
```

Ví dụ:

```json
{
  "id": 1,
  "url": "https://example.com/article"
}
```

Các đội tự thực hiện việc thu thập nội dung từ các URL được cung cấp, tiền xử lý, phân đoạn và xây dựng cơ sở tri thức phục vụ truy hồi.

Đối với dữ liệu tiếng Anh, Ban Tổ chức không cung cấp sẵn danh sách tài liệu. Phạm vi dữ liệu tiếng Anh được giới hạn ở các bài thuộc PubMed (cơ sở dữ liệu lớn về các công bố trong lĩnh vực y sinh và khoa học sức khỏe).

Các đội cần chủ động tìm kiếm các bài PubMed phù hợp với từng câu hỏi và thu thập nội dung để xây dựng cơ sở tri thức. Có thể sử dụng một số API như:

* **NCBI Entrez E-utilities:** dùng để tìm kiếm trực tiếp trên PubMed và lấy danh sách PMID - mã định danh của mỗi bản ghi PubMed.
* **Europe PMC API:** cũng có thể dùng để tìm kiếm các bản ghi PubMed, khi sử dụng cần giới hạn kết quả ở nguồn PubMed.
* **PubTator API:** có thể dùng để lấy nội dung của các bài PubMed theo PMID, bao gồm tiêu đề, abstract và các thông tin y sinh được trích xuất từ bài.

## Ví dụ

Với truy vấn `kidney stone urinary obstruction`, có thể sử dụng NCBI ESearch để lấy danh sách PMID của các bài PubMed phù hợp:

```bash
curl --get "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi" \
  --data-urlencode "db=pubmed" \
  --data-urlencode "term=kidney stone urinary obstruction" \
  --data-urlencode "retmax=100" \
  --data-urlencode "retmode=json"
```

Hoặc sử dụng Europe PMC API và giới hạn kết quả ở các bản ghi thuộc PubMed:

```bash
curl --get "https://www.ebi.ac.uk/europepmc/webservices/rest/search" \
  --data-urlencode "query=SRC:MED AND (kidney stone urinary obstruction)" \
  --data-urlencode "format=json" \
  --data-urlencode "pageSize=100"
```

Sau khi có PMID, có thể sử dụng PubTator API để lấy nội dung của bài. Ví dụ với PMID 26739349:

```bash
curl --get \
  "https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson" \
  --data-urlencode "pmids=26739349"
```

# Quy định chung

## Quyền hủy bỏ, sửa đổi hoặc loại tư cách

Ban Tổ chức Cuộc thi có toàn quyền theo quyết định riêng của mình để chấm dứt, sửa đổi hoặc tạm ngưng cuộc thi.

Khi nộp kết quả cho cuộc thi này, bạn đồng ý cho phép công bố công khai điểm số của mình tại hội thảo của Cuộc thi và trong các kỷ yếu liên quan, theo quyết định của ban tổ chức nhiệm vụ. Điểm số có thể bao gồm nhưng không giới hạn ở các đánh giá định lượng tự động và thủ công, các đánh giá định tính, cùng các chỉ số khác mà ban tổ chức nhiệm vụ cho là phù hợp. Bạn chấp nhận rằng quyết định cuối cùng về việc lựa chọn chỉ số và giá trị điểm số thuộc về ban tổ chức nhiệm vụ.

Khi tham gia cuộc thi, bạn đã chấp nhận các điều khoản và điều kiện của Điều khoản Tham gia và Thỏa thuận Sử dụng Dữ liệu của Nhiệm vụ chung R2AI2026 TRUY HỒI TÀI LIỆU Y KHOA ĐA NGÔN NGỮ, đã được gửi đến email của bạn.

Khi tham gia cuộc thi, bạn khẳng định và thừa nhận rằng bạn đồng ý tuân thủ các luật và quy định hiện hành, và bạn không được xâm phạm bất kỳ bản quyền, tài sản trí tuệ hoặc bằng sáng chế nào của bên khác đối với phần mềm bạn phát triển trong quá trình diễn ra cuộc thi, và sẽ không vi phạm bất kỳ luật và quy định hiện hành nào liên quan đến kiểm soát xuất khẩu cũng như quyền riêng tư và bảo vệ dữ liệu.

Giải thưởng phụ thuộc vào việc Ban Tổ chức Cuộc thi xem xét và xác minh tư cách hợp lệ của thí sinh cũng như sự tuân thủ các quy định này, cùng với sự tuân thủ của các bài nộp thắng giải đối với các yêu cầu nộp bài.

Người tham gia trao cho Ban Tổ chức Cuộc thi quyền sử dụng các bài nộp thắng giải cùng mã nguồn và dữ liệu được tạo ra cho và dùng để tạo ra bài nộp đó vì bất kỳ mục đích nào và không cần phê duyệt thêm.

# Điều kiện tham gia

* Mỗi người tham gia phải tạo một tài khoản để nộp giải pháp cho cuộc thi. Chỉ cho phép một tài khoản cho mỗi người dùng.
* Cuộc thi là công khai, nhưng Ban Tổ chức Cuộc thi có thể quyết định không cho phép tham gia theo cân nhắc riêng của mình.
* Ban Tổ chức Cuộc thi có quyền loại bất kỳ thí sinh nào khỏi cuộc thi nếu, theo quyết định riêng của Ban Tổ chức, họ có cơ sở hợp lý để tin rằng thí sinh đã cố gắng làm suy yếu hoạt động hợp pháp của cuộc thi thông qua gian lận, lừa dối hoặc các hành vi chơi không công bằng khác.

# Đội thi

* Người tham gia được phép lập đội.
* Bạn không được tham gia nhiều hơn một đội. Mỗi thành viên trong đội phải là một cá nhân riêng biệt vận hành một tài khoản riêng.
* Chỉ một tài khoản cho mỗi đội được phê duyệt để nộp kết quả.
