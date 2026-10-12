# Thống kê Domain Nguồn Corpus

## 1. Nguồn dữ liệu

* **Parquet URL:** `corpus/raw/links_corpus.parquet` (cột `id`, `url`).
* **Parquet query:** `queries/query.parquet` (cột `id`, `query`); không dùng làm đầu vào crawler.
* **Snapshot được kiểm tra:** 2026-10-12. Thống kê dưới đây được tính lại từ các file hiện có.

## 2. Phương pháp thống kê

Domain của mỗi URL được xác định bằng hostname: chuyển chữ thường, bỏ dấu chấm cuối và tiền tố `www.`, nhưng giữ nguyên subdomain. Hostname không hợp lệ được thống kê riêng. Số lượng là số hàng URL trong snapshot, không phải số trang crawl thành công hay số tài liệu cuối cùng.

## 3. Kết quả tổng quan

| Chỉ số | Giá trị |
| --- | ---: |
| Tổng số URL | **1.194.469** |
| Hostname chuẩn hóa | **93** |
| URL không có hostname hợp lệ | **0** |
| URL được phân công cho Member A (44 hostname) | **366.854** |
| Query trong `query.parquet` | **1.200** |

## 4. Phân bố số URL theo hostname

| # | Hostname | Số URL |
| -: | --- | ---: |
| 1 | `pubmed.ncbi.nlm.nih.gov` | 240.000 |
| 2 | `suckhoecongdongonline.vn` | 154.503 |
| 3 | `120ask.com` | 98.160 |
| 4 | `suckhoedoisong.vn` | 85.823 |
| 5 | `nhathuoclongchau.com.vn` | 79.598 |
| 6 | `thanhnien.vn` | 72.111 |
| 7 | `cnkang.com` | 40.046 |
| 8 | `ask.39.net` | 32.772 |
| 9 | `laodong.vn` | 31.282 |
| 10 | `phunusuckhoe.giadinhonline.vn` | 27.577 |
| 11 | `familydoctor.com.cn` | 26.819 |
| 12 | `medlatec.vn` | 24.762 |
| 13 | `giadinhonline.vn` | 16.729 |
| 14 | `baohaiphong.vn` | 16.286 |
| 15 | `baonghean.vn` | 15.941 |
| 16 | `vietnamnet.vn` | 15.543 |
| 17 | `baodanang.vn` | 14.500 |
| 18 | `tiemchunglongchau.com.vn` | 13.281 |
| 19 | `baocantho.com.vn` | 12.016 |
| 20 | `hellobacsi.com` | 11.747 |
| 21 | `baoangiang.com.vn` | 10.738 |
| 22 | `vov.vn` | 9.784 |
| 23 | `khoahocphothong.vn` | 8.143 |
| 24 | `youmed.vn` | 7.189 |
| 25 | `vov2.vov.vn` | 6.899 |
| 26 | `zysjonline.com` | 6.591 |
| 27 | `phuyen.baodaklak.vn` | 6.252 |
| 28 | `zhongyibaodian.net` | 6.061 |
| 29 | `suckhoeviet.org.vn` | 5.627 |
| 30 | `baoquangtri.vn` | 5.483 |
| 31 | `pmc-ecm-healthblog.beta.pharmacity.io` | 5.333 |
| 32 | `nhandan.vn` | 5.225 |
| 33 | `baovinhlong.com.vn` | 5.113 |
| 34 | `a-hospital.com` | 4.701 |
| 35 | `tamanhhospital.vn` | 4.261 |
| 36 | `youlai.cn` | 4.139 |
| 37 | `tuoitre.vn` | 3.893 |
| 38 | `qdnd.vn` | 3.700 |
| 39 | `vietnamplus.vn` | 3.695 |
| 40 | `baby.39.net` | 3.368 |
| 41 | `baogialai.com.vn` | 3.290 |
| 42 | `tienphong.vn` | 3.021 |
| 43 | `test.pmphai.com` | 2.989 |
| 44 | `thaythuocvietnam.vn` | 2.927 |
| 45 | `baoquangninh.vn` | 2.912 |
| 46 | `bachmai.gov.vn` | 2.783 |
| 47 | `baochinhphu.vn` | 2.302 |
| 48 | `dantri.com.vn` | 2.063 |
| 49 | `vnexpress.net` | 2.055 |
| 50 | `jbk.39.net` | 2.033 |
| 51 | `baolangson.vn` | 1.981 |
| 52 | `sggp.org.vn` | 1.853 |
| 53 | `baophutho.vn` | 1.288 |
| 54 | `hanoimoi.vn` | 1.283 |
| 55 | `care.39.net` | 1.282 |
| 56 | `benhviennhitrunguong.gov.vn` | 1.200 |
| 57 | `baotayninh.vn` | 1.198 |
| 58 | `heart.39.net` | 1.055 |
| 59 | `fk.39.net` | 928 |
| 60 | `msdmanuals.cn` | 905 |
| 61 | `baothanhhoa.vn` | 782 |
| 62 | `nk.39.net` | 762 |
| 63 | `cancer.39.net` | 736 |
| 64 | `article.iiyi.com` | 729 |
| 65 | `tnb.39.net` | 717 |
| 66 | `wujue.com` | 708 |
| 67 | `woman.39.net` | 687 |
| 68 | `food.39.net` | 594 |
| 69 | `jb39.com` | 527 |
| 70 | `ek.39.net` | 448 |
| 71 | `benhvienvietduc.org` | 425 |
| 72 | `man.39.net` | 382 |
| 73 | `shen.39.net` | 325 |
| 74 | `gan.39.net` | 294 |
| 75 | `wei.39.net` | 225 |
| 76 | `zydcd.com` | 204 |
| 77 | `sj.39.net` | 197 |
| 78 | `fitness.39.net` | 185 |
| 79 | `gk.39.net` | 90 |
| 80 | `pf.39.net` | 85 |
| 81 | `pharmacity.vn` | 69 |
| 82 | `baidianfeng.familydoctor.com.cn` | 60 |
| 83 | `gc.39.net` | 59 |
| 84 | `health.people.com.cn` | 50 |
| 85 | `byby.39.net` | 37 |
| 86 | `qihuangzhishu.com` | 29 |
| 87 | `baidu.com` | 11 |
| 88 | `bingli.iiyi.com` | 5 |
| 89 | `mega.vietnamplus.vn` | 2 |
| 90 | `qy.familydoctor.com.cn` | 2 |
| 91 | `familydoctor.cn` | 2 |
| 92 | `special.vietnamplus.vn` | 1 |
| 93 | `ask.familydoctor.com.cn` | 1 |

## 5. Ghi chú

Corpus hiện có 1.194.469 URL thuộc 93 hostname chuẩn hóa, giảm đáng kể so với snapshot trước. Phân bổ hiện tại cho Member A gồm 366.854 URL trên 44 hostname; chi tiết được duy trì tại [member_01.md](member_01.md). Các số liệu này mô tả URL nguồn, không phải số document/chunk sau crawling, lọc, deduplication hoặc chunking.

Nguồn gốc thu thập và giấy phép của dữ liệu cần được đội dự án ghi nhận từ gói nguồn do cuộc thi cung cấp trước khi tái phân phối.
