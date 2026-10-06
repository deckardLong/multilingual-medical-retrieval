"""
scripts/download_hf_member_b.py
Chỉ tải và lưu 2.19M URL thuộc 53 domain của Member B để tiết kiệm dung lượng và thời gian.
"""
import os
from dotenv import load_dotenv
from urllib.parse import urlsplit
from datasets import load_dataset

load_dotenv()
def is_domain_b(example, domains):
    try:
        h = urlsplit(example["url"]).hostname or ""
        h = h.lower().rstrip(".")
        if h.startswith("www."):
            h = h[4:]
        return h in domains
    except Exception:
        return False

def main() -> None:
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    if not hf_token:
        raise RuntimeError(
            "Chưa cấu hình Hugging Face token. "
            "Đặt biến môi trường HF_TOKEN trước khi chạy script."
        )

    # Đọc 53 domain của Member B
    with open(
        "tasks/01_corpus_collection/crawler/domains_b.txt",
        "r",
        encoding="utf-8",
    ) as f:
        domains_b = {
            line.strip().lower()
            for line in f
            if line.strip() and not line.startswith("#")
        }

    print(f"[*] Đang tải và lọc cho Member B ({len(domains_b)} domains)...")

    ds = load_dataset(
        "AIGuruTinix/ViBioMIR",
        "corpus",
        split="train",
        token=hf_token,
    )

    # Guard trong main là bắt buộc khi dùng multiprocessing trên Windows.
    df_b = ds.filter(
        is_domain_b,
        fn_kwargs={"domains": domains_b},
        num_proc=4,
    )
    print(f"[✓] Số URL của Member B: {len(df_b):,} (kỳ vọng ~2.197.280)")

    df_b.to_parquet("corpus/raw/links_corpus.parquet")
    print("[✓] Đã lưu xong corpus/raw/links_corpus.parquet cho Member B!")


if __name__ == "__main__":
    main()