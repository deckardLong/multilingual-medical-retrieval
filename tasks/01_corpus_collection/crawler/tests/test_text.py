from corpus_crawler.text import normalize_hostname, normalize_text
from corpus_crawler.validation import validate_doc


def test_normalize_text_preserves_unicode_and_collapses_whitespace() -> None:
    assert normalize_text("  a\r\n\r\n\r\nb\u200b\u200f ") == "a\n\nb"


def test_hostname_normalization_is_exact_and_preserves_subdomains() -> None:
    assert normalize_hostname("HTTPS://WWW.Example.COM./path") == "example.com"
    assert normalize_hostname("https://ask.39.net/item") == "ask.39.net"
    assert normalize_hostname("not a url") is None


def test_validate_doc_checks_hash_and_passage_offsets() -> None:
    import hashlib

    text = "Tiêu đề\n\nNội dung y khoa."
    doc = {
        "schema_version": "1.0",
        "uid": "vi:7",
        "doc_id": "7",
        "lang": "vi",
        "source": "btc_url",
        "url": "https://example.org",
        "domain": "example.org",
        "title": "Tiêu đề",
        "text": text,
        "norm_version": "n1",
        "passages": [{"type": "body", "start": 9, "end": len(text)}],
        "text_len": len(text),
        "content_hash": "sha1:" + hashlib.sha1(text.encode("utf-8")).hexdigest(),
        "dup_of": None,
        "fetch": {"status": "ok"},
        "pubmed": None,
        "owner": "a",
        "code_commit": "working-tree",
    }
    validate_doc(doc, "a")
