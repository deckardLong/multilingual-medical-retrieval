"""
scripts/check_blocked_domains.py
Thống kê danh sách domain bị chặn và phân tích nguyên nhân (robots.txt, 403, captcha, v.v.)
    - Disallowed by robots.txt: Website có file robots.txt cấm bot cào chuyên mục đó 
    - HTTP 403; access not bypassed: Server dùng Cloudflare/WAF chặn IP của bạn.
    - Possible captcha/access challenge: Trang web trả về giao diện xác minh hình ảnh "Tôi không phải là người máy".
    - Cross-domain redirect not fetched: Bài viết bị chuyển hướng sang một tên miền lạ ngoài danh sách 53 domain của bạn
"""
import sqlite3
import pandas as pd

DB_PATH = "corpus/viz/state-b.sqlite3"

print(f"[*] Đang phân tích các URL bị chặn từ database: {DB_PATH}...\n")

conn = sqlite3.connect(DB_PATH)

# Truy vấn thống kê các domain bị chặn và lý do lỗi
query = """
SELECT 
    domain,
    json_extract(log_json, '$.error') AS error_reason,
    COUNT(*) AS blocked_count
FROM urls 
WHERE status = 'done' 
  AND json_extract(log_json, '$.status') = 'blocked'
GROUP BY domain, error_reason
ORDER BY blocked_count DESC;
"""

df_blocked = pd.read_sql_query(query, conn)
conn.close()

if df_blocked.empty:
    print("[✓] Tuyệt vời! Chưa có domain nào bị chặn.")
else:
    print(f"[!] Tìm thấy {len(df_blocked)} nhóm domain gặp vấn đề truy cập:\n")
    print(df_blocked.to_string(index=False))

    # In ra 5 URL cụ thể bị chặn để kiểm tra thủ công trên trình duyệt
    print("\n" + "="*80)
    print("MẪU 5 URL BỊ CHẶN ĐỂ BẠN THỬ BẬT TRÌNH DUYỆT KIỂM TRA:")
    conn = sqlite3.connect(DB_PATH)
    sample_query = """
    SELECT url, domain, json_extract(log_json, '$.error') as reason 
    FROM urls 
    WHERE json_extract(log_json, '$.status') = 'blocked' 
    LIMIT 5;
    """
    df_sample = pd.read_sql_query(sample_query, conn)
    conn.close()
    for idx, row in df_sample.iterrows():
        print(f"{idx+1}. [{row['domain']}] {row['url']}")
        print(f"   -> Lý do: {row['reason']}")