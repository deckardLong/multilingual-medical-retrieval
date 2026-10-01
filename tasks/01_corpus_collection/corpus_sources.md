# Thống kê Domain Nguồn Corpus

## 1. Nguồn dữ liệu

* **Parquet đầu vào:** `corpus/raw/links_corpus.parquet`
* **Cột URL:** `url`
* **Script thống kê:** `corpus_demo.py`
* **Phạm vi phân tích:** 4.394.718 URL trong snapshot corpus.

## 2. Phương pháp thống kê

Domain của mỗi URL được xác định dựa trên **hostname** của URL.

Quy trình chuẩn hóa hostname:

1. Trích xuất hostname từ URL.
2. Chuyển hostname về chữ thường.
3. Loại bỏ dấu chấm ở cuối hostname nếu có.
4. Loại bỏ tiền tố `www.` nếu có.
5. Giữ nguyên subdomain, do đó các hostname như `ask.39.net` và `39.net` được xem là **hai domain riêng biệt**.
6. Các URL không có hostname hợp lệ được thống kê riêng.

> **Lưu ý:** Số lượng của mỗi domain biểu thị **số URL xuất hiện trong snapshot**, không đồng nghĩa với số trang đã crawl thành công hoặc số tài liệu hợp lệ sau quá trình ingestion.

## 3. Kết quả tổng quan

| Chỉ số                     |       Giá trị |
| -------------------------- | ------------: |
| Tổng số URL                | **4.394.718** |
| Tổng số domain             |        **97** |
| URL không có domain hợp lệ |         **0** |

Như vậy, toàn bộ **4.394.718 URL** trong snapshot đều có hostname hợp lệ và được phân loại vào **97 domain** khác nhau.

## 4. Phân bố số URL theo domain

Danh sách dưới đây được sắp xếp theo **số lượng URL giảm dần**:

|  # | Domain                                  |  Số URL |
| -: | --------------------------------------- | ------: |
|  1 | `cnkang.com`                            | 963.438 |
|  2 | `120ask.com`                            | 918.479 |
|  3 | `familydoctor.com.cn`                   | 447.453 |
|  4 | `ask.39.net`                            | 337.375 |
|  5 | `zysjonline.com`                        | 243.347 |
|  6 | `a-hospital.com`                        | 169.339 |
|  7 | `suckhoecongdongonline.vn`              | 154.503 |
|  8 | `zhongyibaodian.net`                    | 146.700 |
|  9 | `suckhoedoisong.vn`                     |  85.823 |
| 10 | `nhathuoclongchau.com.vn`               |  79.598 |
| 11 | `zydcd.com`                             |  78.680 |
| 12 | `thanhnien.vn`                          |  72.111 |
| 13 | `wujue.com`                             |  53.341 |
| 14 | `youlai.cn`                             |  46.119 |
| 15 | `laodong.vn`                            |  31.282 |
| 16 | `baby.39.net`                           |  27.621 |
| 17 | `phunusuckhoe.giadinhonline.vn`         |  27.577 |
| 18 | `vinmec.com`                            |  26.129 |
| 19 | `bingli.iiyi.com`                       |  24.990 |
| 20 | `medlatec.vn`                           |  24.762 |
| 21 | `qihuangzhishu.com`                     |  23.637 |
| 22 | `jbk.39.net`                            |  19.142 |
| 23 | `giadinhonline.vn`                      |  16.729 |
| 24 | `baohaiphong.vn`                        |  16.286 |
| 25 | `baonghean.vn`                          |  15.941 |
| 26 | `vietnamnet.vn`                         |  15.543 |
| 27 | `care.39.net`                           |  15.134 |
| 28 | `test.pmphai.com`                       |  15.120 |
| 29 | `baodanang.vn`                          |  14.500 |
| 30 | `tiemchunglongchau.com.vn`              |  13.281 |
| 31 | `fitness.39.net`                        |  12.066 |
| 32 | `baocantho.com.vn`                      |  12.016 |
| 33 | `hellobacsi.com`                        |  11.747 |
| 34 | `woman.39.net`                          |  11.687 |
| 35 | `food.39.net`                           |  11.024 |
| 36 | `baoangiang.com.vn`                     |  10.738 |
| 37 | `fk.39.net`                             |   9.812 |
| 38 | `vov.vn`                                |   9.784 |
| 39 | `cancer.39.net`                         |   8.415 |
| 40 | `khoahocphothong.vn`                    |   8.143 |
| 41 | `jb39.com`                              |   7.306 |
| 42 | `youmed.vn`                             |   7.189 |
| 43 | `vov2.vov.vn`                           |   6.899 |
| 44 | `nk.39.net`                             |   6.650 |
| 45 | `phuyen.baodaklak.vn`                   |   6.252 |
| 46 | `msdmanuals.cn`                         |   6.173 |
| 47 | `heart.39.net`                          |   5.965 |
| 48 | `article.iiyi.com`                      |   5.641 |
| 49 | `suckhoeviet.org.vn`                    |   5.627 |
| 50 | `baoquangtri.vn`                        |   5.483 |
| 51 | `pmc-ecm-healthblog.beta.pharmacity.io` |   5.333 |
| 52 | `man.39.net`                            |   5.320 |
| 53 | `nhandan.vn`                            |   5.225 |
| 54 | `baovinhlong.com.vn`                    |   5.113 |
| 55 | `gan.39.net`                            |   5.027 |
| 56 | `tamanhhospital.vn`                     |   4.261 |
| 57 | `tnb.39.net`                            |   4.178 |
| 58 | `wei.39.net`                            |   3.894 |
| 59 | `tuoitre.vn`                            |   3.893 |
| 60 | `baidianfeng.familydoctor.com.cn`       |   3.798 |
| 61 | `qdnd.vn`                               |   3.700 |
| 62 | `vietnamplus.vn`                        |   3.695 |
| 63 | `baogialai.com.vn`                      |   3.290 |
| 64 | `shen.39.net`                           |   3.223 |
| 65 | `ek.39.net`                             |   3.222 |
| 66 | `tienphong.vn`                          |   3.021 |
| 67 | `thaythuocvietnam.vn`                   |   2.927 |
| 68 | `baoquangninh.vn`                       |   2.912 |
| 69 | `bachmai.gov.vn`                        |   2.783 |
| 70 | `baidu.com`                             |   2.631 |
| 71 | `baochinhphu.vn`                        |   2.302 |
| 72 | `dantri.com.vn`                         |   2.063 |
| 73 | `gk.39.net`                             |   2.059 |
| 74 | `vnexpress.net`                         |   2.055 |
| 75 | `baolangson.vn`                         |   1.981 |
| 76 | `sggp.org.vn`                           |   1.853 |
| 77 | `gc.39.net`                             |   1.746 |
| 78 | `pf.39.net`                             |   1.538 |
| 79 | `health.people.com.cn`                  |   1.348 |
| 80 | `baophutho.vn`                          |   1.288 |
| 81 | `hanoimoi.vn`                           |   1.283 |
| 82 | `benhviennhitrunguong.gov.vn`           |   1.200 |
| 83 | `baotayninh.vn`                         |   1.198 |
| 84 | `sj.39.net`                             |     942 |
| 85 | `baothanhhoa.vn`                        |     782 |
| 86 | `byby.39.net`                           |     439 |
| 87 | `benhvienvietduc.org`                   |     425 |
| 88 | `pharmacity.vn`                         |      69 |
| 89 | `familydoctor.cn`                       |      44 |
| 90 | `qy.familydoctor.com.cn`                |      40 |
| 91 | `v.familydoctor.com.cn`                 |      10 |
| 92 | `ask.familydoctor.com.cn`               |       3 |
| 93 | `mega.vietnamplus.vn`                   |       2 |
| 94 | `yanglao.familydoctor.com.cn`           |       2 |
| 95 | `fk.99.com.cn`                          |       1 |
| 96 | `special.vietnamplus.vn`                |       1 |
| 97 | `ypk.familydoctor.com.cn`               |       1 |

## 5. Nhận xét

Corpus có **4.394.718 URL thuộc 97 domain**, với phân bố không đồng đều giữa các nguồn. Một số domain chiếm số lượng URL rất lớn, trong khi nhiều domain chỉ đóng góp một lượng nhỏ URL.

Đặc biệt, các domain thuộc nhóm website thông tin y tế, tư vấn sức khỏe và bệnh viện chiếm phần lớn corpus. Bên cạnh đó, corpus cũng bao gồm các nguồn báo chí và truyền thông như `thanhnien.vn`, `vietnamnet.vn`, `vov.vn`, `tuoitre.vn`, `nhandan.vn`, `dantri.com.vn` và `vnexpress.net`.

Do thống kê được thực hiện trên **URL trong snapshot**, các con số trên nên được hiểu là **phân bố nguồn URL ban đầu**, không phải phân bố số lượng document/chunk cuối cùng trong vector database. Sau các bước crawling, cleaning, filtering, deduplication và chunking, phân bố dữ liệu thực tế có thể thay đổi.
