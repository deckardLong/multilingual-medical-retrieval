from dataclasses import replace

from corpus_crawler.extract import make_records
from corpus_crawler.fetch import FetchResult
from corpus_crawler.settings import load_settings


def test_extracts_and_normalizes_vietnamese_article() -> None:
    settings = replace(load_settings(), min_text_chars=100)
    paragraph = (
        "Bác sĩ khuyến cáo người bệnh cần theo dõi triệu chứng và trao đổi "
        "với nhân viên y tế. "
        * 8
    )
    html = (
        "<html><head><title>Hướng dẫn sức khỏe</title></head><body>"
        f"<article><h1>Hướng dẫn sức khỏe</h1><p>{paragraph}</p></article>"
        "</body></html>"
    ).encode("utf-8")
    result = FetchResult(
        status="ok",
        http_status=200,
        fetched_at="2026-10-02T00:00:00+07:00",
        final_url="https://cnkang.com/example",
        body=html,
        error=None,
        attempts=1,
        nbytes=len(html),
        encoding="utf-8",
    )

    log, doc = make_records(
        9, "https://cnkang.com/example", "cnkang.com", result, settings
    )

    assert doc is not None
    assert doc["lang"] == "vi"
    assert doc["text_len"] == len(doc["text"])
    assert doc["content_hash"].startswith("sha1:")
    assert log["status"] == "ok"
    assert all(
        0 <= passage["start"] <= passage["end"] <= len(doc["text"])
        for passage in doc["passages"]
    )
