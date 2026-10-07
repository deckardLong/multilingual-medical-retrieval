"""
scripts/inspect_shard.py
Đọc và in nội dung bài viết mẫu từ file shard .jsonl.zst
để kiểm tra xem văn bản có sạch không, có bị dính menu/quảng cáo hay không
"""
import json
import zstandard as zstd

SHARD_PATH = "corpus/viz/docs/b/viz-b-00001.jsonl.zst"

print(f"[*] Đang đọc dữ liệu từ: {SHARD_PATH}\n" + "="*80)

dctx = zstd.ZstdDecompressor()
with open(SHARD_PATH, "rb") as f:
    with dctx.stream_reader(f) as reader:
        # Đọc theo từng dòng
        buffer = ""
        count = 0
        while chunk := reader.read(65536):
            buffer += chunk.decode("utf-8", errors="replace")
            lines = buffer.split("\n")
            buffer = lines[-1]  # Giữ lại phần chưa đủ 1 dòng
            
            for line in lines[:-1]:
                if not line.strip():
                    continue
                doc = json.loads(line)
                count += 1
                
                print(f"--- BÀI VIẾT #{count} ---")
                print(f"• ID nguồn (doc_id): {doc['doc_id']}")
                print(f"• Ngôn ngữ:          {doc['lang'].upper()}")
                print(f"• Domain:            {doc['domain']}")
                print(f"• Tiêu đề (Title):   {doc.get('title', '(Không có)')}")
                print(f"• Độ dài Text:       {doc['text_len']:,} ký tự")
                print(f"• Trích đoạn đầu:")
                print(doc['text'][:300] + ("..." if len(doc['text']) > 300 else ""))
                print("="*80)
                
                if count >= 3:  # Chỉ xem 3 bài mẫu
                    break
            if count >= 3:
                break